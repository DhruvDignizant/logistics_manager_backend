"""
Route Request Trip Map for Phase 2.4.

Maps accepted route requests to created trips (idempotency).
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from backend.app.db.session import Base


class RouteRequestTripMap(Base):
    """
    Route Request to Trip mapping.
    
    Ensures idempotency: one trip per accepted route request.
    """
    __tablename__ = "route_request_trip_map"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    route_request_id = Column(Integer, ForeignKey('hub_route_requests.id'), unique=True, nullable=False, index=True)
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False, index=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RouteRequestTripMap(request_id={self.route_request_id}, trip_id={self.trip_id})>"
