"""
ML configuration for Phase 2.3.

Feature flags and thresholds for ML route matching.
"""

# ML Feature Flags
ML_ENABLED = True  # Master switch for ML scoring (can be env var)

# Training Thresholds
MIN_TRAINING_SAMPLES = 100  # Minimum samples before enabling ML predictions
MIN_TEST_SAMPLES = 10  # Minimum samples for model training

# Scoring Thresholds
MIN_ROUTE_SCORE = 0.3  # Minimum score to include route in suggestions
MAX_SUGGESTIONS = 10  # Maximum number of routes to suggest

# Static Scoring Weights (fallback when ML disabled)
STATIC_WEIGHTS = {
    "distance_score": 0.35,
    "weight_score": 0.25,
    "volume_score": 0.25,
    "window_score": 0.15
}
