"""
Route Request Decision schemas for Phase 2.3.3.

Schemas for Fleet Owners to accept/reject route requests.
"""

from pydantic import BaseModel, Field
from typing import Optional


class RouteRequestAccept(BaseModel):
    """Schema for accepting a route request."""
    # No additional fields needed - acceptance is implicit
    pass


class RouteRequestReject(BaseModel):
    """Schema for rejecting a route request."""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for rejection")


class RouteRequestDecisionResponse(BaseModel):
    """Response after decision."""
    id: int
    status: str  # ACCEPTED or REJECTED
    decision_reason: Optional[str]
    decided_at: str
    ml_training_recorded: bool
