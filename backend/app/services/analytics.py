"""
Analytics Service for Phase 2.7.

Handles data aggregation and complex queries for dashboards.
Focused on READ-ONLY operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict, Any

from backend.app.models.trip import Trip
from backend.app.models.trip_charge import TripCharge
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.trip_enums import TripStatus
from backend.app.models.parcel import Parcel
from backend.app.models.parcel_enums import ParcelStatus
from backend.app.models.user import User
from backend.app.models.enums import UserRole
from backend.app.models.ml_training_data import MLRouteTrainingData
from backend.app.schemas.analytics import (
    FleetOverviewStats, VehicleUtilization, 
    HubOverviewStats, AdminSystemStats, MLPerformanceStats
)


class AnalyticsService:

    @staticmethod
    async def get_fleet_overview(db: AsyncSession, fleet_owner_id: int) -> FleetOverviewStats:
        """Get high-level stats for a Fleet Owner."""
        
        # 1. Total Revenue (Sum of Trip Charges where fleet is payee)
        revenue_query = select(func.sum(TripCharge.total_charge)).where(
            TripCharge.fleet_owner_id == fleet_owner_id
        )
        revenue = (await db.execute(revenue_query)).scalar() or 0.0
        
        # 2. Vehicle Counts
        active_vehicles_query = select(func.count(FleetVehicle.id)).where(
            FleetVehicle.owner_id == fleet_owner_id,
            FleetVehicle.is_active == True # Simple active check, or join with Trips for "In Use"?
            # Prompt asked for "Active Fleet" -> "vehicles currently in use (IN_PROGRESS)"
            # Let's count vehicles currently assigned to IN_PROGRESS trips.
        )
        # Actually, let's look at trips.
        active_trips_query = select(func.count(Trip.id)).where(
            Trip.fleet_owner_id == fleet_owner_id,
            Trip.status == TripStatus.IN_PROGRESS
        )
        active_trips = (await db.execute(active_trips_query)).scalar() or 0
        
        # We can use active_trips as proxy for active vehicles if 1:1.
        
        # 3. Completed Trips
        completed_trips_query = select(func.count(Trip.id)).where(
            Trip.fleet_owner_id == fleet_owner_id,
            Trip.status == TripStatus.COMPLETED
        )
        completed_trips = (await db.execute(completed_trips_query)).scalar() or 0
        
        # 4. Total Drivers
        drivers_query = select(func.count(User.id)).where(
            User.fleet_owner_id == fleet_owner_id,
            User.role == UserRole.DRIVER
        )
        total_drivers = (await db.execute(drivers_query)).scalar() or 0

        return FleetOverviewStats(
            total_revenue=revenue,
            active_vehicles_count=active_trips, # Proxy
            active_trips_count=active_trips,
            completed_trips_count=completed_trips,
            total_drivers_count=total_drivers
        )

    @staticmethod
    async def get_vehicle_utilization(db: AsyncSession, fleet_owner_id: int) -> List[VehicleUtilization]:
        """Get performance breakdown by vehicle."""
        # Join Vehicles with Trips and Charges
        # This is a bit complex. We'll iterate active vehicles for now or use GROUP BY.
        
        # Query: Vehicle ID, Plate, Count(Trips), Sum(Charges)
        # We need to join Trip -> TripCharge
        stmt = select(
            FleetVehicle.id,
            FleetVehicle.license_plate,
            FleetVehicle.status,
            func.count(Trip.id).label("total_trips"),
            func.coalesce(func.sum(TripCharge.total_charge), 0).label("total_revenue")
        ).outerjoin(Trip, Trip.vehicle_id == FleetVehicle.id)\
         .outerjoin(TripCharge, TripCharge.trip_id == Trip.id)\
         .where(FleetVehicle.owner_id == fleet_owner_id)\
         .group_by(FleetVehicle.id)
        
        results = await db.execute(stmt)
        
        data = []
        for row in results:
            data.append(VehicleUtilization(
                vehicle_id=row.id,
                license_plate=row.license_plate,
                status=row.status.value,
                total_trips=row.total_trips,
                total_revenue=row.total_revenue
            ))
        return data

    @staticmethod
    async def get_hub_overview(db: AsyncSession, hub_owner_id: int) -> HubOverviewStats:
        """Get stats for Hub Owner."""
        
        # 1. Total Spend
        spend_query = select(func.sum(TripCharge.total_charge)).where(
            TripCharge.hub_owner_id == hub_owner_id
        )
        spend = (await db.execute(spend_query)).scalar() or 0.0
        
        # 2. Total Parcels Delivered
        delivered_query = select(func.count(Parcel.id)).where(
            Parcel.hub_owner_id == hub_owner_id,
            Parcel.status == ParcelStatus.DELIVERED
        )
        delivered = (await db.execute(delivered_query)).scalar() or 0
        
        # 3. Active Parcels
        active_query = select(func.count(Parcel.id)).where(
            Parcel.hub_owner_id == hub_owner_id,
            Parcel.status.in_([ParcelStatus.IN_TRANSIT, ParcelStatus.PICKED_UP])
        )
        active = (await db.execute(active_query)).scalar() or 0
        
        # 4. Active Requests (Pending Route Requests)
        from backend.app.models.hub_route_request import HubRouteRequest
        # To avoid circular import issues if placed at top, usually ok inside method or if guarded.
        # But we imported it in main.py so it's registered.
        # Ideally import specific model at top.
        
        req_query = select(func.count(HubRouteRequest.id)).where(
            HubRouteRequest.hub_owner_id == hub_owner_id,
            HubRouteRequest.status == "PENDING" # Assuming 'PENDING' string or enum
        )
        requests = (await db.execute(req_query)).scalar() or 0
        
        return HubOverviewStats(
            total_spend=spend,
            total_parcels_delivered=delivered,
            active_parcels_count=active,
            active_requests_count=requests
        )

    @staticmethod
    async def get_admin_system_stats(db: AsyncSession) -> AdminSystemStats:
        """Get system-wide health stats."""
        
        users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        trips = (await db.execute(select(func.count(Trip.id)))).scalar() or 0
        
        # Total Volume (KG moved)
        # Sum of weight from TripCharges
        vol_query = select(func.sum(TripCharge.weight_kg))
        volume = (await db.execute(vol_query)).scalar() or 0.0
        
        # Total Revenue (Platform Level - Sum of all charges)
        rev_query = select(func.sum(TripCharge.total_charge))
        revenue = (await db.execute(rev_query)).scalar() or 0.0
        
        # Counts
        fleets = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.FLEET_OWNER))).scalar() or 0
        hubs = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.HUB_OWNER))).scalar() or 0
        
        return AdminSystemStats(
            total_users=users,
            total_fleets=fleets,
            total_hubs=hubs,
            total_trips=trips,
            total_volume_processed_kg=volume,
            total_platform_revenue=revenue
        )

    @staticmethod
    async def get_ml_performance(db: AsyncSession) -> MLPerformanceStats:
        """Get ML Model performance metrics."""
        
        total = (await db.execute(select(func.count(MLRouteTrainingData.id)))).scalar() or 0
        
        accepted = (await db.execute(
            select(func.count(MLRouteTrainingData.id)).where(MLRouteTrainingData.outcome == 1)
        )).scalar() or 0
        
        rejected = total - accepted
        rate = (accepted / total) if total > 0 else 0.0
        
        return MLPerformanceStats(
            total_training_records=total,
            total_suggestions=total, # Every training record was a suggestion
            accepted_suggestions=accepted,
            rejected_suggestions=rejected,
            acceptance_rate=rate
        )
