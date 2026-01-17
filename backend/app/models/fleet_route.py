"""
Fleet Route database model for Phase 2.3.

Fleet Owners create routes between locations with capacity constraints.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.route_enums import RouteStatus


class FleetRoute(Base):
    """
    Fleet Route model.
    
    A route is a transportation path created by a Fleet Owner with origin,
    destination, and capacity constraints.
    """
    __tablename__ = "fleet_routes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Ownership - Route belongs to Fleet Owner
    fleet_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Route details
    route_name = Column(String(200), nullable=False)
    
    # Origin location
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    origin_address = Column(String(500), nullable=True)
    
    # Destination location
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    destination_address = Column(String(500), nullable=True)
    
    # Capacity constraints
    max_weight_kg = Column(Float, nullable=False)
    max_volume_cm3 = Column(Float, nullable=False)  # length * width * height
    
    # Vehicle assignment (optional - allows attaching specific vehicle to route)
    vehicle_id = Column(Integer, ForeignKey('fleet_vehicles.id'), nullable=True, index=True)
    
    # Status
    status = Column(Enum(RouteStatus), default=RouteStatus.ACTIVE, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<FleetRoute(id={self.id}, name='{self.route_name}', owner_id={self.fleet_owner_id})>"
