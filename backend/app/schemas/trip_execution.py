"""
Trip execution schemas for Phase 2.5.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TripStartResponse(BaseModel):
    """Response after starting a trip."""
    trip_id: int
    status: str  # IN_PROGRESS
    started_at: datetime
    vehicle_locked: bool
    

class LocationRecord(BaseModel):
    """Schema for recording GPS location."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: Optional[float] = Field(None, gt=0)
    recorded_at: datetime


class LocationRecordResponse(BaseModel):
    """Response after recording location."""
    trip_id: int
    location_id: int
    recorded: bool


class StopCompleteResponse(BaseModel):
    """Response after completing a stop."""
    stop_id: int
    trip_id: int
    status: str  # COMPLETED
    completed_at: datetime
    

class TripCompleteResponse(BaseModel):
    """Response after completing a trip."""
    trip_id: int
    status: str  # COMPLETED
    completed_at: datetime
    vehicle_unlocked: bool
    total_stops_completed: int


class TripLocationResponse(BaseModel):
    """GPS location response."""
    id: int
    latitude: float
    longitude: float
    accuracy_meters: Optional[float]
    recorded_at: datetime
    
    class Config:
        from_attributes = True
