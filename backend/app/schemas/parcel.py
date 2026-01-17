"""
Parcel Pydantic schemas for Phase 2.2.

Defines request and response models for parcel management.
"""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List
from backend.app.models.parcel_enums import ParcelStatus


class ParcelCreate(BaseModel):
    """Schema for creating a new parcel."""
    reference_code: str = Field(..., min_length=1, max_length=100, description="Unique parcel reference")
    description: Optional[str] = Field(None, max_length=500, description="Parcel description")
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms")
    length_cm: float = Field(..., gt=0, description="Length in centimeters")
    width_cm: float = Field(..., gt=0, description="Width in centimeters")
    height_cm: float = Field(..., gt=0, description="Height in centimeters")
    quantity: int = Field(default=1, ge=1, description="Number of items")
    delivery_due_date: date = Field(..., description="Delivery due date")


class ParcelUpdate(BaseModel):
    """Schema for updating an existing parcel."""
    description: Optional[str] = Field(None, max_length=500)
    weight_kg: Optional[float] = Field(None, gt=0)
    length_cm: Optional[float] = Field(None, gt=0)
    width_cm: Optional[float] = Field(None, gt=0)
    height_cm: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=1)
    delivery_due_date: Optional[date] = None
    status: Optional[ParcelStatus] = None


class ParcelResponse(BaseModel):
    """Schema for parcel response."""
    id: int
    hub_id: int
    hub_owner_id: int
    reference_code: str
    description: Optional[str]
    weight_kg: float
    length_cm: float
    width_cm: float
    height_cm: float
    quantity: int
    delivery_due_date: date
    status: ParcelStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ParcelListResponse(BaseModel):
    """Schema for paginated parcel list."""
    parcels: List[ParcelResponse]
    total: int
    page: int
    page_size: int
