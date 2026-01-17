"""
Billing Schemas for Phase 2.6.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from backend.app.models.billing_enums import SettlementStatus


class PricingRuleCreate(BaseModel):
    """Schema for creating a pricing rule."""
    rule_name: str = Field(..., min_length=1, max_length=100)
    base_rate_per_km: float = Field(..., gt=0)
    weight_surcharge_per_kg: float = Field(..., ge=0)
    effective_from: datetime


class PricingRuleResponse(BaseModel):
    """Schema for displaying a pricing rule."""
    id: int
    rule_name: str
    base_rate_per_km: float
    weight_surcharge_per_kg: float
    effective_from: datetime
    effective_until: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminSettlementActionResponse(BaseModel):
    """Response for settlement actions."""
    settlement_id: int
    status: str
    updated_at: datetime


class TripChargeResponse(BaseModel):
    """Schema for displaying trip charges."""
    id: int
    trip_id: int
    distance_km: float
    weight_kg: float
    total_charge: float
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class SettlementResponse(BaseModel):
    """Schema for displaying settlements."""
    id: int
    total_amount: float
    status: str
    created_at: datetime
    paid_at: Optional[datetime]
    
    class Config:
        from_attributes = True

