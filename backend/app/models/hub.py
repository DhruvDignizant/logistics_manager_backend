"""
Hub database model for Phase 2.1.

Hub Owners can create and manage multiple hubs with address and geolocation.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from backend.app.db.session import Base


class Hub(Base):
    """
    Hub model for logistics platform.
    
    A hub is a physical location managed by a Hub Owner.
    Each hub has an address and geolocation coordinates.
    """
    __tablename__ = "hubs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Ownership - Hub belongs to one Hub Owner
    hub_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Hub details
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    
    # Geolocation
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Status (soft delete)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Hub(id={self.id}, name='{self.name}', owner_id={self.hub_owner_id}, active={self.is_active})>"
