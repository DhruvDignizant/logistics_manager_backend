"""
Archived Trip Location Model for Phase 3.

Table for long-term storage of old GPS data.
"""

from sqlalchemy import Column, Integer, Float, DateTime, Index
from backend.app.db.session import Base


class ArchivedTripLocation(Base):
    """
    Archived Trip Location.
    Same structure as TripLocation but designed for cold storage.
    Optimized for bulk inserts, not real-time query.
    """
    __tablename__ = "archived_trip_locations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    original_id = Column(Integer, nullable=False) # Keep reference
    trip_id = Column(Integer, nullable=False, index=True)
    driver_id = Column(Integer, nullable=False)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=False)
    
    # Partitioning would be ideal in Postgres (e.g., by month), 
    # but sticking to standard SQLAlchemy model for compatibility.
