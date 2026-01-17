"""
Hub Route Request model for Phase 2.3.

Tracks route requests made by Hub Owners for their parcels.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, String
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.route_enums import RouteRequestStatus


class HubRouteRequest(Base):
    """
    Hub Route Request model.
    
    Tracks when a Hub Owner views/requests a route suggestion for a parcel.
    Used for feedback collection and ML training data generation.
    """
    __tablename__ = "hub_route_requests"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    hub_id = Column(Integer, ForeignKey('hubs.id'), nullable=False, index=True)
    parcel_id = Column(Integer, ForeignKey('parcels.id'), nullable=False, index=True)
    route_id = Column(Integer, ForeignKey('fleet_routes.id'), nullable=False, index=True)
    hub_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Request status
    status = Column(Enum(RouteRequestStatus), default=RouteRequestStatus.PENDING, nullable=False, index=True)
    
    # Decision tracking (Phase 2.3.3)
    decision_reason = Column(String(500), nullable=True)  # Optional reason for reject
    decided_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<HubRouteRequest(id={self.id}, parcel_id={self.parcel_id}, route_id={self.route_id}, status='{self.status.value}')>"
