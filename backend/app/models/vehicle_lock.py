"""
Vehicle Lock database model for Phase 2.5.

Ensures only one IN_PROGRESS trip per vehicle through DB-level unique constraint.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from backend.app.db.session import Base


class VehicleLock(Base):
    """
    Vehicle Lock model.
    
    Enforces one IN_PROGRESS trip per vehicle through unique constraint.
    Vehicle is locked when trip starts, released when trip completes.
    """
    __tablename__ = "vehicle_locks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    vehicle_id = Column(Integer, ForeignKey('fleet_vehicles.id'), nullable=False, index=True)
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False, index=True)
    locked_by_driver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Lock lifecycle
    locked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    
    # Unique constraint: only one active lock per vehicle
    __table_args__ = (
        Index('ix_vehicle_locks_active', 'vehicle_id', unique=True, 
              postgresql_where=Column('released_at').is_(None)),
    )
    
    def __repr__(self):
        return f"<VehicleLock(vehicle_id={self.vehicle_id}, trip_id={self.trip_id}, active={self.released_at is None})>"
