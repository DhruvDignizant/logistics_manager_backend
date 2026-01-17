"""
ML Scoring service for route-parcel matching - Phase 2.3.

Provides ML-based and fallback scoring with explainability.
Uses locally-hosted Logistic Regression (no external AI APIs).
"""

import math
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.ml_route_weight import MLRouteWeight
from backend.app.services.ml_features import extract_features, normalize_features


# Configuration
MIN_TRAINING_SAMPLES = 100  # Minimum samples required before enabling ML
ML_ENABLED = True  # Feature flag (can be set via env var)


async def get_active_ml_model(db: AsyncSession) -> Optional[MLRouteWeight]:
    """
    Get the currently active ML model from database.
    
    Returns:
        Active ML model or None if no model is active
    """
    result = await db.execute(
        select(MLRouteWeight).where(MLRouteWeight.is_active == True)
    )
    return result.scalar_one_or_none()


def sigmoid(x: float) -> float:
    """Sigmoid activation function for logistic regression."""
    return 1.0 / (1.0 + math.exp(-x))


def ml_predict_score(features: Dict[str, float], 
                     weights: Dict[str, float], 
                     intercept: float,
                     normalization_params: Dict[str, Dict[str, float]]) -> Tuple[float, Dict[str, float]]:
    """
    Predict route-parcel compatibility using logistic regression.
    
    Args:
        features: Raw feature dictionary
        weights: Model weights
        intercept: Model intercept
        normalization_params: Feature normalization parameters
    
    Returns:
        (probability_score, feature_contributions)
    """
    # Normalize features using stored parameters
    normalized = normalize_features(features, normalization_params)
    
    # Compute linear combination: z = w1*x1 + w2*x2 + ... + intercept
    z = intercept
    feature_contributions = {}
    
    for feature_name, feature_value in normalized.items():
        if feature_name in weights:
            contribution = weights[feature_name] * feature_value
            z += contribution
            feature_contributions[feature_name] = contribution
    
    # Apply sigmoid to get probability
    probability = sigmoid(z)
    
    return round(probability, 4), feature_contributions


def fallback_static_score(features: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """
    Fallback static scoring when ML is disabled or not trained.
    
    Uses weighted average of features with predefined weights.
    
    Returns:
        (score, feature_contributions)
    """
    # Static weights (hand-crafted, balanced)
    static_weights = {
        "distance_score": 0.35,  # Distance is most important
        "weight_score": 0.25,
        "volume_score": 0.25,
        "window_score": 0.15
    }
    
    total_score = 0.0
    contributions = {}
    
    for feature_name, feature_value in features.items():
        if feature_name in static_weights:
            contribution = feature_value * static_weights[feature_name]
            total_score += contribution
            contributions[feature_name] = contribution
    
    return round(total_score, 4), contributions


async def score_route_for_parcel(
    db: AsyncSession,
    hub_lat: float, hub_lng: float,
    parcel_weight_kg: float, parcel_volume_cm3: float, parcel_due_days: int,
    route_origin_lat: float, route_origin_lng: float,
    route_max_weight_kg: float, route_max_volume_cm3: float
) -> Dict:
    """
    Score a route for a parcel using ML or fallback.
    
    Returns:
        {
            "score": float,
            "method": "ml" | "static",
            "model_version": str | None,
            "explainability": {feature_name: contribution},
            "features": {feature_name: raw_value}
        }
    """
    # Extract raw features
    features = extract_features(
        hub_lat, hub_lng,
        parcel_weight_kg, parcel_volume_cm3, parcel_due_days,
        route_origin_lat, route_origin_lng,
        route_max_weight_kg, route_max_volume_cm3
    )
    
    # Try to use ML model
    if ML_ENABLED:
        ml_model = await get_active_ml_model(db)
        
        if ml_model and ml_model.training_samples >= MIN_TRAINING_SAMPLES:
            # Use ML scoring
            score, contributions = ml_predict_score(
                features,
                ml_model.feature_weights,
                ml_model.intercept,
                ml_model.normalization_params
            )
            
            return {
                "score": score,
                "method": "ml",
                "model_version": ml_model.model_version,
                "explainability": contributions,
                "features": features
            }
    
    # Fallback to static scoring
    score, contributions = fallback_static_score(features)
    
    return {
        "score": score,
        "method": "static",
        "model_version": None,
        "explainability": contributions,
        "features": features
    }
