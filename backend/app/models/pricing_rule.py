"""
Pricing Rule database model for Phase 2.6.

Defines pricing configuration for trip charge calculation.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from backend.app.db.session import Base


class PricingRule(Base):
    """
    Pricing Rule model.
    
    Defines the rates used to calculate trip charges.
    Only one rule is active at a time (globally for now).
    """
    __tablename__ = "pricing_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Rule details
    rule_name = Column(String(100), nullable=False)
    base_rate_per_km = Column(Float, nullable=False)  # Cost per kilometer
    weight_surcharge_per_kg = Column(Float, nullable=False)  # Cost per kg
    
    # Validity
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_by_admin_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<PricingRule(id={self.id}, name='{self.rule_name}', base_rate={self.base_rate_per_km})>"
