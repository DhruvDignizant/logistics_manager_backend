"""
Route Discovery schemas for Phase 2.3.2.

Response models for ML-powered route suggestions.
"""

from pydantic import BaseModel
from typing import List, Dict, Optional
from backend.app.schemas.fleet_route import FleetRouteResponse


class RouteSuggestionExplainability(BaseModel):
    """Feature contributions for explainability."""
    distance_contribution: float
    weight_contribution: float
    volume_contribution: float
    window_contribution: float


class RouteSuggestion(BaseModel):
    """Single route suggestion with ML score and explainability."""
    route: FleetRouteResponse
    ml_score: float
    scoring_method: str  # "ml" or "static"
    explainability: RouteSuggestionExplainability
    raw_features: Dict[str, float]


class RouteSuggestionsResponse(BaseModel):
    """Response containing ranked route suggestions for a parcel."""
    parcel_id: int
    suggestions: List[RouteSuggestion]
    total_routes_evaluated: int
    ml_enabled: bool
    model_version: Optional[str]


class RouteRequestCreate(BaseModel):
    """Schema for creating a route request."""
    # No additional fields needed - parcel_id and route_id from URL
    pass


class RouteRequestResponse(BaseModel):
    """Schema for route request response."""
    id: int
    hub_id: int
    parcel_id: int
    route_id: int
    hub_owner_id: int
    status: str
    requested_at: str
    
    class Config:
        from_attributes = True


class RouteRequestListResponse(BaseModel):
    """Schema for list of route requests."""
    requests: List[RouteRequestResponse]
    total: int
    page: int
    page_size: int
