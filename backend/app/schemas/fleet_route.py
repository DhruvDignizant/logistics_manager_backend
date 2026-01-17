"""
Fleet Route Pydantic schemas for Phase 2.3.1.

Defines request and response models for fleet route management.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from backend.app.models.route_enums import RouteStatus


class FleetRouteCreate(BaseModel):
    """Schema for creating a new fleet route."""
    route_name: str = Field(..., min_length=1, max_length=200, description="Route name")
    
    # Origin location
    origin_lat: float = Field(..., ge=-90, le=90, description="Origin latitude")
    origin_lng: float = Field(..., ge=-180, le=180, description="Origin longitude")
    origin_address: Optional[str] = Field(None, max_length=500, description="Origin address")
    
    # Destination location
    destination_lat: float = Field(..., ge=-90, le=90, description="Destination latitude")
    destination_lng: float = Field(..., ge=-180, le=180, description="Destination longitude")
    destination_address: Optional[str] = Field(None, max_length=500, description="Destination address")
    
    # Capacity constraints
    max_weight_kg: float = Field(..., gt=0, description="Maximum weight capacity in kg")
    max_volume_cm3: float = Field(..., gt=0, description="Maximum volume capacity in cm³")


class FleetRouteUpdate(BaseModel):
    """Schema for updating an existing fleet route."""
    route_name: Optional[str] = Field(None, min_length=1, max_length=200)
    origin_lat: Optional[float] = Field(None, ge=-90, le=90)
    origin_lng: Optional[float] = Field(None, ge=-180, le=180)
    origin_address: Optional[str] = Field(None, max_length=500)
    destination_lat: Optional[float] = Field(None, ge=-90, le=90)
    destination_lng: Optional[float] = Field(None, ge=-180, le=180)
    destination_address: Optional[str] = Field(None, max_length=500)
    max_weight_kg: Optional[float] = Field(None, gt=0)
    max_volume_cm3: Optional[float] = Field(None, gt=0)
    status: Optional[RouteStatus] = None


class FleetRouteResponse(BaseModel):
    """Schema for fleet route response."""
    id: int
    fleet_owner_id: int
    route_name: str
    origin_lat: float
    origin_lng: float
    origin_address: Optional[str]
    destination_lat: float
    destination_lng: float
    destination_address: Optional[str]
    max_weight_kg: float
    max_volume_cm3: float
    status: RouteStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FleetRouteListResponse(BaseModel):
    """Schema for paginated fleet route list."""
    routes: List[FleetRouteResponse]
    total: int
    page: int
    page_size: int
