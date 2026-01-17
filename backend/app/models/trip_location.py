"""
Trip Location database model for Phase 2.5.

Stores GPS breadcrumb trail for live trip tracking.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from backend.app.db.session import Base


class TripLocation(Base):
    """
    Trip Location model.
    
    Records GPS coordinates for live trip tracking.
    Creates a breadcrumb trail of driver's journey.
    """
    __tablename__ = "trip_locations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # GPS coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)  # GPS accuracy in meters
    
    # Timing
    recorded_at = Column(DateTime(timezone=True), nullable=False)  # When GPS was recorded
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # When inserted to DB
    
    def __repr__(self):
        return f"<TripLocation(trip_id={self.trip_id}, lat={self.latitude}, lng={self.longitude})>"
