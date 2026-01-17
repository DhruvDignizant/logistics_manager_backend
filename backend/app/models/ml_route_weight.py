"""
ML Route Weight database model for Phase 2.3.

Stores trained ML model weights, normalization parameters, and metadata.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from backend.app.db.session import Base


class MLRouteWeight(Base):
    """
    ML Route Weight model.
    
    Stores logistic regression model weights, intercept, normalization parameters,
    and evaluation metrics. Supports model versioning and atomic model swaps.
    """
    __tablename__ = "ml_route_weights"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Model versioning
    model_version = Column(String(50), unique=True, nullable=False, index=True)
    
    # Model parameters (Logistic Regression)
    feature_weights = Column(JSON, nullable=False)  # {"distance": -0.42, "weight": 0.31, ...}
    intercept = Column(Float, nullable=False)
    
    # Feature normalization parameters (stored for consistency)
    # Format: {"feature_name": {"mean": X, "std": Y}}
    normalization_params = Column(JSON, nullable=False)
    
    # Model evaluation metrics
    accuracy_score = Column(Float, nullable=True)
    precision_score = Column(Float, nullable=True)
    recall_score = Column(Float, nullable=True)
    training_samples = Column(Integer, nullable=False)
    
    # Model status
    is_active = Column(Boolean, default=False, nullable=False, index=True)  # Only one active model at a time
    
    # Timestamps
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<MLRouteWeight(version='{self.model_version}', active={self.is_active}, accuracy={self.accuracy_score})>"
