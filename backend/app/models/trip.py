"""
Trip database model for Phase 2.4.

Trips are explicitly created by Fleet Owners from accepted route requests.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.trip_enums import TripStatus


class Trip(Base):
    """
    Trip model.
    
    A trip is explicitly created by a Fleet Owner from an accepted route request.
    It represents the actual execution of transporting parcels.
    """
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Ownership - Trip belongs to Fleet Owner
    fleet_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Route and vehicle assignment
    route_id = Column(Integer, ForeignKey('fleet_routes.id'), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey('fleet_vehicles.id'), nullable=True, index=True)
    
    # Driver assignment (optional initially, can be assigned later)
    driver_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Status
    status = Column(Enum(TripStatus), default=TripStatus.PLANNED, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Trip(id={self.id}, route_id={self.route_id}, status='{self.status.value}')>"
