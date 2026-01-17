"""
Fleet Vehicle database model for Phase 2.3.1a.

Fleet Owners register vehicles with capacity and identification details.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.app.db.session import Base


class FleetVehicle(Base):
    """
    Fleet Vehicle model.
    
    A vehicle is registered by a Fleet Owner with capacity constraints
    and identification details. Vehicles can be assigned to routes.
    """
    __tablename__ = "fleet_vehicles"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Ownership - Vehicle belongs to Fleet Owner
    fleet_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Vehicle identification
    vehicle_number = Column(String(100), unique=True, nullable=False, index=True)
    vehicle_type = Column(String(100), nullable=True)  # e.g., "Truck", "Van", "Bike"
    
    # Capacity constraints (authoritative source)
    max_weight_kg = Column(Float, nullable=False)
    max_volume_cm3 = Column(Float, nullable=False)
    
    # Physical dimensions (for loading calculations)
    length_cm = Column(Float, nullable=True)
    width_cm = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    
    # Vehicle details
    fuel_type = Column(String(50), nullable=True)  # e.g., "Diesel", "Petrol", "Electric"
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<FleetVehicle(id={self.id}, number='{self.vehicle_number}', owner_id={self.fleet_owner_id})>"
