"""
ML Route Training Data model for Phase 2.3.

Stores historical route-parcel pairings with features and success labels for ML training.
"""

from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.app.db.session import Base


class MLRouteTrainingData(Base):
    """
    ML Route Training Data model.
    
    Stores feature vectors and labels for training the route matching model.
    Each record represents a route-parcel pairing with computed features
    and a success label (1 = successful match, 0 = unsuccessful).
    """
    __tablename__ = "ml_route_training_data"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References (for audit trail)
    route_id = Column(Integer, ForeignKey('fleet_routes.id'), nullable=False, index=True)
    parcel_id = Column(Integer, ForeignKey('parcels.id'), nullable=False, index=True)
    
    # Feature vector (computed at pairing time)
    distance_score = Column(Float, nullable=False)  # Normalized distance hub to route origin
    weight_score = Column(Float, nullable=False)    # Weight capacity match
    volume_score = Column(Float, nullable=False)    # Volume capacity match
    window_score = Column(Float, nullable=False)    # Delivery window overlap
    
    # Label (ground truth)
    was_successful = Column(Boolean, nullable=False, index=True)  # 1 = accepted/completed, 0 = rejected/failed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<MLTrainingData(route_id={self.route_id}, parcel_id={self.parcel_id}, success={self.was_successful})>"
