"""
Settlement database model for Phase 2.6.

Aggregates multiple trip charges into a single payment obligation.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.billing_enums import SettlementStatus


class Settlement(Base):
    """
    Settlement model.
    
    Represents a periodic aggregation of charges to be paid from a Hub Owner to a Fleet Owner.
    Follows a strict approval workflow: PENDING -> APPROVED -> PAID.
    """
    __tablename__ = "settlements"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Parties
    hub_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # Payer
    fleet_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # Payee
    
    # Financials
    total_amount = Column(Float, nullable=False)
    
    # Status
    status = Column(Enum(SettlementStatus), default=SettlementStatus.PENDING, nullable=False, index=True)
    
    # Approval Flow
    approved_by_admin_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Payment Flow
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Settlement(id={self.id}, status='{self.status.value}', amount={self.total_amount})>"
