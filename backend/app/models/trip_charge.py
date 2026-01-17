"""
Trip Charge database model for Phase 2.6.

Stores the calculated financial charge for a completed trip.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.app.db.session import Base


class TripCharge(Base):
    """
    Trip Charge model.
    
    Represents the financial cost of a specific trip.
    Calculated automatically upon trip completion based on active pricing rule.
    Links the Payer (Hub Owner) and Payee (Fleet Owner).
    """
    __tablename__ = "trip_charges"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Relationships
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False, unique=True, index=True)
    hub_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # Payer
    fleet_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # Payee
    pricing_rule_id = Column(Integer, ForeignKey('pricing_rules.id'), nullable=False)
    
    # Calculation Metrics
    distance_km = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    
    # Financials
    base_charge = Column(Float, nullable=False)  # distance * rate
    surcharge = Column(Float, nullable=False)  # weight * rate
    total_charge = Column(Float, nullable=False)  # base + surcharge
    
    # Settlement linkage (can be null if not yet settled)
    settlement_id = Column(Integer, ForeignKey('settlements.id'), nullable=True, index=True)
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<TripCharge(id={self.id}, trip_id={self.trip_id}, total={self.total_charge})>"
