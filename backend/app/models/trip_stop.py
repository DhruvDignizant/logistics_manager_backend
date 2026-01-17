"""
Trip Stop database model for Phase 2.4.

Stops represent pickup and delivery points in a trip.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.trip_enums import TripStopType, TripStopStatus


class TripStop(Base):
    """
    Trip Stop model.
    
    Represents a pickup or delivery stop in a trip.
    Each stop is linked to a hub (for parcel) or destination.
    """
    __tablename__ = "trip_stops"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Trip reference
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False, index=True)
    
    # Parcel being transported
    parcel_id = Column(Integer, ForeignKey('parcels.id'), nullable=False, index=True)
    
    # Stop details
    stop_type = Column(Enum(TripStopType), nullable=False)  # PICKUP or DELIVERY
    sequence_number = Column(Integer, nullable=False)  # Order in trip (1, 2, 3, ...)
    
    # Location (from hub or route destination)
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    location_address = Column(String(500), nullable=True)
    
    # Status
    status = Column(Enum(TripStopStatus), default=TripStopStatus.PENDING, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<TripStop(id={self.id}, trip_id={self.trip_id}, type='{self.stop_type.value}', seq={self.sequence_number})>"
