"""
Hub Pydantic schemas for Phase 2.1.

Defines request and response models for hub management.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class HubCreate(BaseModel):
    """Schema for creating a new hub."""
    name: str = Field(..., min_length=1, max_length=200, description="Hub name")
    address: str = Field(..., min_length=1, max_length=500, description="Full address")
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., min_length=1, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")


class HubUpdate(BaseModel):
    """Schema for updating an existing hub."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    pincode: Optional[str] = Field(None, min_length=1, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class HubResponse(BaseModel):
    """Schema for hub response."""
    id: int
    hub_owner_id: int
    name: str
    address: str
    city: str
    state: str
    country: str
    pincode: str
    latitude: Optional[float]
    longitude: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HubListResponse(BaseModel):
    """Schema for paginated hub list."""
    hubs: List[HubResponse]
    total: int
    page: int
    page_size: int
