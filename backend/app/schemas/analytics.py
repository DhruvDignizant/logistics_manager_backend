"""
Analytics Schemas for Phase 2.7.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MetricTuple(BaseModel):
    """Generic metric response."""
    label: str
    value: float | int


class FleetOverviewStats(BaseModel):
    """Dashboard stats for Fleet Owners."""
    total_revenue: float
    active_vehicles_count: int
    active_trips_count: int
    completed_trips_count: int
    total_drivers_count: int


class VehicleUtilization(BaseModel):
    """Vehicle performance stats."""
    vehicle_id: int
    license_plate: str
    total_trips: int
    total_revenue: float
    status: str


class HubOverviewStats(BaseModel):
    """Dashboard stats for Hub Owners."""
    total_spend: float
    total_parcels_delivered: int
    active_parcels_count: int
    active_requests_count: int


class AdminSystemStats(BaseModel):
    """System-wide stats for Admins."""
    total_users: int
    total_fleets: int
    total_hubs: int
    total_trips: int
    total_volume_processed_kg: float
    total_platform_revenue: float


class MLPerformanceStats(BaseModel):
    """ML Model performance stats."""
    total_suggestions: int
    accepted_suggestions: int
    rejected_suggestions: int
    acceptance_rate: float
    total_training_records: int
