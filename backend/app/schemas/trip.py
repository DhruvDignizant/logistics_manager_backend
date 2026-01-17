"""
Trip schemas for Phase 2.4.1.

Schemas for trip creation and visibility.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TripStopResponse(BaseModel):
    """Schema for trip stop response."""
    id: int
    trip_id: int
    parcel_id: int
    stop_type: str  # PICKUP or DELIVERY
    sequence_number: int
    location_lat: float
    location_lng: float
    location_address: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TripResponse(BaseModel):
    """Schema for trip response."""
    id: int
    fleet_owner_id: int
    route_id: int
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    stops: List[TripStopResponse] = []
    
    class Config:
        from_attributes = True


class TripListResponse(BaseModel):
    """Schema for paginated trip list."""
    trips: List[TripResponse]
    total: int
    page: int
    page_size: int


class TripCreateResponse(BaseModel):
    """Response after trip creation."""
    trip: TripResponse
    route_request_id: int
    capacity_validated: bool
    stops_generated: int
