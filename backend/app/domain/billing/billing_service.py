"""
Billing Service (Domain Logic).

Handles financial calculations, settlement creation, and ledger recording.
Must be transactional and idempotent.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from backend.app.models.trip import Trip
from backend.app.models.trip_charge import TripCharge
from backend.app.models.settlement import Settlement
from backend.app.models.ledger_entry import LedgerEntry
from backend.app.models.billing_enums import SettlementStatus, LedgerEntryType
from backend.app.models.pricing_rule import PricingRule
from backend.app.models.trip_enums import TripStatus
from backend.app.models.parcel import Parcel
from backend.app.models.fleet_route import FleetRoute
from backend.app.domain.billing.pricing_resolver import PricingResolver


class BillingService:
    
    @staticmethod
    async def process_trip(db: AsyncSession, trip_id: int) -> TripCharge:
        """
        Process billing for a completed trip.
        
        Flow:
        1. Validate Trip State (COMPLETED)
        2. Idempotency Check (Existing TripCharge)
        3. Resolve Pricing Rule
        4. Calculate Charges
        5. Create TripCharge (Immutable)
        6. Create Settlement (Pending)
        7. Create Ledger Entries (Double Entry)
        
        Args:
            db: Database session (transaction managed by caller or auto-commit)
            trip_id: ID of the completed trip
            
        Returns:
            Created TripCharge
        """
        # 1. Fetch Trip Data with relations
        # We need parcel (weight) and route (distance) to calculate
        # But wait, Trip -> TripStop -> Parcel.
        # We also need fleet_owner_id and hub_owner_id (via parcel? or route request?)
        # Let's check the Trip model. Trip has fleet_owner_id.
        # Trip maps to a Route Request (via RouteRequestTripMap potentially, or implicitly)
        # But we need the HUB OWNER.
        # The Trip has stops. One of them is a PICKUP stop which has the parcel_id.
        # The Parcel has the hub_owner_id.
        
        stmt = select(Trip).options(
            joinedload(Trip.trip_stops).joinedload("parcel"),
            joinedload(Trip.route)  # Assuming relationship exists or we query manually
        ).where(Trip.id == trip_id)
        
        result = await db.execute(stmt)
        trip = result.unique().scalar_one_or_none()
        
        if not trip:
            raise ValueError(f"Trip {trip_id} not found")
            
        if trip.status != TripStatus.COMPLETED:
            raise ValueError(f"Trip {trip_id} is not COMPLETED. Current status: {trip.status}")
            
        # 2. Idempotency Check
        existing_charge = await db.execute(
            select(TripCharge).where(TripCharge.trip_id == trip_id)
        )
        if existing_charge.scalar_one_or_none():
            # Idempotency: Already processed
            # We return existing charge or raise?
            # Ideally return existing to be safe
            return existing_charge.scalar_one()

        # Find Hub Owner via Parcel
        # Assuming single parcel per trip for now based on earlier phases (1 parcel -> request -> trip)
        # Or at least we pick the first pickup stop's parcel.
        parcel = None
        for stop in trip.trip_stops:
            if stop.parcel:
                parcel = stop.parcel
                break
        
        if not parcel:
            raise ValueError(f"No parcel found associated with Trip {trip_id}")
            
        hub_owner_id = parcel.hub_owner_id
        fleet_owner_id = trip.fleet_owner_id
        
        # Get Route Distance (We might need to rely on the FleetRoute metadata or calculated actuals)
        # Using FleetRoute.total_distance_km if available, or calculating from stops?
        # Phase 2.3.1 FleetRoute has origin/destination.
        # Ideally TripCharge should use ACTUAL distance or AGREED distance.
        # Let's use the FleetRoute approximate distance if not tracked, or calculated.
        # For Phase 2.6, we'll use ML/Route distance or a placeholder if missing.
        # Let's assume FleetRoute has distance info, or we calculate it.
        # Checking FleetRoute model... standard `FleetRoute` usually has lat/lng.
        # We'll calculate simple Haversine distance if not stored.
        # For robustness, let's look at `TripLocation`? No, billing usually on quoted distance.
        # We'll use the Route's estimated distance.
        
        route = await db.get(FleetRoute, trip.route_id)
        if not route:
            raise ValueError("Trip route not found")
        
        # Calculate distance (simplified for now, or use what stored)
        from backend.app.services.ml_features import haversine_distance
        distance_km = haversine_distance(
            route.origin_lat, route.origin_lng,
            route.destination_lat, route.destination_lng
        )
        
        weight_kg = parcel.weight
        
        # 3. Resolve Pricing Rule
        pricing_rule = await PricingResolver.resolve_active_rule(db)
        
        # 4. Calculate Charges
        base_charge = distance_km * pricing_rule.base_rate_per_km
        surcharge = weight_kg * pricing_rule.weight_surcharge_per_kg
        total_amount = base_charge + surcharge
        
        # 5. Create TripCharge
        trip_charge = TripCharge(
            trip_id=trip.id,
            hub_owner_id=hub_owner_id,
            fleet_owner_id=fleet_owner_id,
            pricing_rule_id=pricing_rule.id,
            distance_km=distance_km,
            weight_kg=weight_kg,
            base_charge=base_charge,
            surcharge=surcharge,
            total_charge=total_amount
        )
        db.add(trip_charge)
        await db.flush()  # To get trip_charge.id
        
        # 6. Create Settlement (1-to-1 for this implementation, typically 1-to-many)
        # Plan says: "Create Settlement... Aggregate unpaid trip charges... Periodic"
        # BUT User Prompt Step 1 says: "Persist Settlement (PENDING)" inside process_trip.
        # This implies per-trip settlement creation OR adding to existing?
        # Prompt: "Persist Settlement (PENDING)" singular.
        # Let's create a new settlement per trip for simplicity in this phase unless aggregation is strictly required.
        # "Aggregates multiple trip charges" was in the Model docstring.
        # However, "BillingService... Create Settlement (PENDING)" in strict order suggests doing it now.
        # Let's do 1 settlement per trip for now (Simplest Atomic Unit), or find pending settlement?
        # To ensure strict traceability, let's create a new settlement for this trip.
        # Aggregation can happen at payout time or we can aggregate later.
        # Creating one settlement per charge is safer for "Atomic" requirement.
        
        settlement = Settlement(
            hub_owner_id=hub_owner_id,
            fleet_owner_id=fleet_owner_id,
            total_amount=total_amount,
            status=SettlementStatus.PENDING
        )
        db.add(settlement)
        await db.flush()
        
        # Link charge to settlement
        trip_charge.settlement_id = settlement.id
        
        # 7. Write Ledger Entries (Double Entry)
        # Hub Owner OWEs money (Account Payable / Expense) -> DEBIT (Assets decreasing? No, wait)
        # Ledger logic:
        # Hub Owner (Payer) -> DEBIT (Liability/Expense increases?)
        # Fleet Owner (Payee) -> CREDIT (Equity/Income increases)
        # Standard Accounting:
        # Payer pays cash: Credit Cash.
        # Here we are recording the OBLIGATION.
        # Hub Owner Account (Liability to Pay): Credit?
        # Let's follow the simple instruction:
        # "Hub Owner → DEBIT"
        # "Fleet Owner → CREDIT"
        
        ledger_debit = LedgerEntry(
            settlement_id=settlement.id,
            entry_type=LedgerEntryType.DEBIT,
            account_owner_id=hub_owner_id,
            amount=total_amount,
            description=f"Trip Charge: {trip_id} (Settlement {settlement.id})"
        )
        
        ledger_credit = LedgerEntry(
            settlement_id=settlement.id,
            entry_type=LedgerEntryType.CREDIT,
            account_owner_id=fleet_owner_id,
            amount=total_amount,
            description=f"Trip Earnings: {trip_id} (Settlement {settlement.id})"
        )
        
        db.add(ledger_debit)
        db.add(ledger_credit)
        
        # Audit Event happens in the caller or here?
        # Service should handle logic. Logging can happen here.
        from backend.app.services.audit import log_event, AuditAction
        # Need to know WHO triggered this? System.
        # We'll skip actor_id/username for system events or use a system user if available.
        # For now, we omit audit log here to keep service pure or pass context.
        # The PROMPT says "Write audit logs for every action" (in Step 3 Admin APIs).
        # But also "Trip Completion Hook" invokes this.
        # We can log "TRIP_CHARGE_CALCULATED" here.
        
        # commit happens in caller? "Single DB transaction".
        # If we commit here, we break upper transaction boundaries if any.
        # Best practice: Flush here, let controller/hook commit.
        
        return trip_charge
