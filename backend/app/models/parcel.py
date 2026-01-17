"""
Parcel database model for Phase 2.2.

Hub Owners can create and manage parcels within their hubs.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Date, Boolean
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.parcel_enums import ParcelStatus


class Parcel(Base):
    """
    Parcel model for logistics platform.
    
    A parcel is a shipment managed by a Hub Owner within a specific hub.
    Each parcel has dimensions, weight, and delivery requirements.
    """
    __tablename__ = "parcels"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Ownership - Parcel belongs to a hub and its owner
    hub_id = Column(Integer, ForeignKey('hubs.id'), nullable=False, index=True)
    hub_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Parcel identification
    reference_code = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    # Physical properties
    weight_kg = Column(Float, nullable=False)
    length_cm = Column(Float, nullable=False)
    width_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Delivery information
    delivery_due_date = Column(Date, nullable=False)
    
    # Status
    status = Column(Enum(ParcelStatus), default=ParcelStatus.PENDING, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Parcel(id={self.id}, ref='{self.reference_code}', hub_id={self.hub_id}, status='{self.status.value}')>"
