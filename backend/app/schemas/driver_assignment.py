"""
Driver Assignment schemas for Phase 2.4.2.
"""

from pydantic import BaseModel
from typing import Optional


class DriverAssignment(BaseModel):
    """Schema for assigning a driver to a trip."""
    driver_id: int


class DriverAssignmentResponse(BaseModel):
    """Response after driver assignment."""
    trip_id: int
    driver_id: int
    status: str  # PENDING (after assignment from PLANNED)
    connectivity_validated: bool
    connectivity_reason: str
