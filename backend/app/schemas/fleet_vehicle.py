"""
Fleet Vehicle Pydantic schemas for Phase 2.3.1a.

Defines request and response models for vehicle management.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class FleetVehicleCreate(BaseModel):
    """Schema for registering a new fleet vehicle."""
    vehicle_number: str = Field(..., min_length=1, max_length=100, description="Unique vehicle registration number")
    vehicle_type: Optional[str] = Field(None, max_length=100, description="Vehicle type (e.g., Truck, Van)")
    
    # Capacity constraints
    max_weight_kg: float = Field(..., gt=0, description="Maximum weight capacity in kg")
    max_volume_cm3: float = Field(..., gt=0, description="Maximum volume capacity in cm³")
    
    # Physical dimensions (optional)
    length_cm: Optional[float] = Field(None, gt=0, description="Vehicle length in cm")
    width_cm: Optional[float] = Field(None, gt=0, description="Vehicle width in cm")
    height_cm: Optional[float] = Field(None, gt=0, description="Vehicle height in cm")
    
    # Vehicle details
    fuel_type: Optional[str] = Field(None, max_length=50, description="Fuel type (e.g., Diesel, Electric)")


class FleetVehicleUpdate(BaseModel):
    """Schema for updating an existing fleet vehicle."""
    vehicle_type: Optional[str] = Field(None, max_length=100)
    max_weight_kg: Optional[float] = Field(None, gt=0)
    max_volume_cm3: Optional[float] = Field(None, gt=0)
    length_cm: Optional[float] = Field(None, gt=0)
    width_cm: Optional[float] = Field(None, gt=0)
    height_cm: Optional[float] = Field(None, gt=0)
    fuel_type: Optional[str] = Field(None, max_length=50)


class FleetVehicleResponse(BaseModel):
    """Schema for fleet vehicle response."""
    id: int
    fleet_owner_id: int
    vehicle_number: str
    vehicle_type: Optional[str]
    max_weight_kg: float
    max_volume_cm3: float
    length_cm: Optional[float]
    width_cm: Optional[float]
    height_cm: Optional[float]
    fuel_type: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FleetVehicleListResponse(BaseModel):
    """Schema for paginated fleet vehicle list."""
    vehicles: List[FleetVehicleResponse]
    total: int
    page: int
    page_size: int
