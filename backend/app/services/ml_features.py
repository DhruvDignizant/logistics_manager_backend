"""
Feature extraction service for ML route matching - Phase 2.3.

Computes features for route-parcel compatibility scoring.
"""

import math
from typing import Dict


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)
    
    Returns:
        Distance in kilometers
    """
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def calculate_distance_score(hub_lat: float, hub_lng: float, 
                            route_origin_lat: float, route_origin_lng: float) -> float:
    """
    Calculate distance compatibility score.
    
    Returns normalized score where lower is better (inverted).
    Score = 1 / (1 + distance_km)
    
    Close distances get high scores (e.g., 1km → 0.5)
    Far distances get low scores (e.g., 100km → 0.01)
    """
    distance_km = haversine_distance(hub_lat, hub_lng, route_origin_lat, route_origin_lng)
    
    # Normalize: closer = higher score
    score = 1.0 / (1.0 + distance_km)
    return round(score, 4)


def calculate_weight_score(parcel_weight_kg: float, route_max_weight_kg: float) -> float:
    """
    Calculate weight capacity compatibility score.
    
    Returns:
        1.0 if parcel fits comfortably (< 80% capacity)
        0.5-1.0 if parcel fits but near limit
        0.0 if parcel exceeds capacity
    """
    if parcel_weight_kg > route_max_weight_kg:
        return 0.0  # Cannot accommodate
    
    utilization = parcel_weight_kg / route_max_weight_kg
    
    if utilization <= 0.8:
        return 1.0  # Comfortable fit
    else:
        # Linear decrease from 1.0 to 0.5 as utilization goes from 80% to 100%
        return 1.0 - (utilization - 0.8) * 2.5
    
    return round(max(0.0, min(1.0, score)), 4)


def calculate_volume_score(parcel_volume_cm3: float, route_max_volume_cm3: float) -> float:
    """
    Calculate volume capacity compatibility score.
    
    Same logic as weight score.
    """
    if parcel_volume_cm3 > route_max_volume_cm3:
        return 0.0
    
    utilization = parcel_volume_cm3 / route_max_volume_cm3
    
    if utilization <= 0.8:
        return 1.0
    else:
        score = 1.0 - (utilization - 0.8) * 2.5
    
    return round(max(0.0, min(1.0, score)), 4)


def calculate_window_score(parcel_due_days: int) -> float:
    """
    Calculate delivery window score.
    
    Args:
        parcel_due_days: Days until parcel delivery due date
    
    Returns:
        Higher score for more time available (less urgency)
        1.0 for 7+ days
        0.0 for overdue
    """
    if parcel_due_days < 0:
        return 0.0  # Overdue
    
    if parcel_due_days >= 7:
        return 1.0  # Plenty of time
    
    # Linear scale from 0 to 1 over 7 days
    score = parcel_due_days / 7.0
    return round(score, 4)


def extract_features(hub_lat: float, hub_lng: float,
                     parcel_weight_kg: float, parcel_volume_cm3: float, parcel_due_days: int,
                     route_origin_lat: float, route_origin_lng: float,
                     route_max_weight_kg: float, route_max_volume_cm3: float) -> Dict[str, float]:
    """
    Extract all features for route-parcel compatibility.
    
    Returns:
        Dictionary of feature scores (all normalized 0-1)
    """
    return {
        "distance_score": calculate_distance_score(hub_lat, hub_lng, route_origin_lat, route_origin_lng),
        "weight_score": calculate_weight_score(parcel_weight_kg, route_max_weight_kg),
        "volume_score": calculate_volume_score(parcel_volume_cm3, route_max_volume_cm3),
        "window_score": calculate_window_score(parcel_due_days)
    }


def normalize_features(features: Dict[str, float], normalization_params: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    Normalize features using stored mean and std from training.
    
    Args:
        features: Raw feature dictionary
        normalization_params: {"feature_name": {"mean": X, "std": Y}}
    
    Returns:
        Normalized features (z-score normalization)
    """
    normalized = {}
    for feature_name, value in features.items():
        if feature_name in normalization_params:
            mean = normalization_params[feature_name]["mean"]
            std = normalization_params[feature_name]["std"]
            
            # Avoid division by zero
            if std > 0:
                normalized[feature_name] = (value - mean) / std
            else:
                normalized[feature_name] = 0.0
        else:
            # If no normalization params, use raw value
            normalized[feature_name] = value
    
    return normalized
