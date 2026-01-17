"""
ML Training pipeline for route matching - Phase 2.3.

Trains logistic regression model using historical data.
Implements atomic model swap and normalization persistence.
"""

from typing import Dict, List, Tuple
import numpy as np
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.ml_training_data import MLRouteTrainingData
from backend.app.models.ml_route_weight import MLRouteWeight


try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


async def collect_training_data(db: AsyncSession) -> Tuple[np.ndarray, np.ndarray, Dict[str, Dict[str, float]]]:
    """
    Collect training data from database.
    
    Returns:
        (X: feature matrix, y: labels, normalization_params)
    """
    # Fetch all training data
    result = await db.execute(
        select(MLRouteTrainingData).order_by(MLRouteTrainingData.created_at.desc())
    )
    training_data = result.scalars().all()
    
    if not training_data:
        raise ValueError("No training data available")
    
    # Extract features and labels
    X = []
    y = []
    
    for record in training_data:
        features = [
            record.distance_score,
            record.weight_score,
            record.volume_score,
            record.window_score
        ]
        X.append(features)
        y.append(1 if record.was_successful else 0)
    
    X = np.array(X)
    y = np.array(y)
    
    # Compute normalization parameters (mean and std for each feature)
    scaler = StandardScaler()
    scaler.fit(X)
    
    normalization_params = {
        "distance_score": {"mean": float(scaler.mean_[0]), "std": float(scaler.scale_[0])},
        "weight_score": {"mean": float(scaler.mean_[1]), "std": float(scaler.scale_[1])},
        "volume_score": {"mean": float(scaler.mean_[2]), "std": float(scaler.scale_[2])},
        "window_score": {"mean": float(scaler.mean_[3]), "std": float(scaler.scale_[3])}
    }
    
    # Normalize features
    X_normalized = scaler.transform(X)
    
    return X_normalized, y, normalization_params


async def train_ml_model(db: AsyncSession) -> Dict:
    """
    Train logistic regression model using collected data.
    
    Implements:
    1. Data collection
    2. Train/test split
    3. Model training
    4. Evaluation
    5. Atomic model swap (old model stays active until new model succeeds)
    
    Returns:
        Training results dictionary
    """
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn is not installed. Run: pip install scikit-learn")
    
    # Collect training data
    X, y, normalization_params = await collect_training_data(db)
    
    if len(X) < 10:
        raise ValueError(f"Insufficient training data: {len(X)} samples (minimum 10 required)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train logistic regression model
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    
    # Extract model parameters
    feature_weights = {
        "distance_score": float(model.coef_[0][0]),
        "weight_score": float(model.coef_[0][1]),
        "volume_score": float(model.coef_[0][2]),
        "window_score": float(model.coef_[0][3])
    }
    intercept = float(model.intercept_[0])
    
    # Generate new model version
    model_version = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Create new model record (NOT yet active)
    new_model = MLRouteWeight(
        model_version=model_version,
        feature_weights=feature_weights,
        intercept=intercept,
        normalization_params=normalization_params,
        accuracy_score=accuracy,
        precision_score=precision,
        recall_score=recall,
        training_samples=len(X),
        is_active=False  # Keep old model active until we commit
    )
    
    db.add(new_model)
    await db.flush()  # Get ID without committing
    
    # Atomic swap: Deactivate old model, activate new model
    await db.execute(
        select(MLRouteWeight).where(MLRouteWeight.is_active == True)
    )
    old_models = (await db.execute(
        select(MLRouteWeight).where(MLRouteWeight.is_active == True)
    )).scalars().all()
    
    for old_model in old_models:
        old_model.is_active = False
    
    new_model.is_active = True
    new_model.activated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(new_model)
    
    return {
        "model_version": model_version,
        "training_samples": len(X),
        "test_samples": len(X_test),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "feature_weights": feature_weights,
        "intercept": intercept,
        "normalization_params": normalization_params,
        "activated": True
    }


async def get_model_stats(db: AsyncSession) -> Dict:
    """
    Get statistics about the currently active ML model.
    
    Returns:
        Model statistics or None if no model active
    """
    result = await db.execute(
        select(MLRouteWeight).where(MLRouteWeight.is_active == True)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        return {
            "ml_enabled": False,
            "message": "No active model"
        }
    
    return {
        "ml_enabled": True,
        "model_version": model.model_version,
        "training_samples": model.training_samples,
        "accuracy": model.accuracy_score,
        "precision": model.precision_score,
        "recall": model.recall_score,
        "feature_weights": model.feature_weights,
        "intercept": model.intercept,
        "trained_at": model.trained_at.isoformat(),
        "activated_at": model.activated_at.isoformat() if model.activated_at else None
    }
