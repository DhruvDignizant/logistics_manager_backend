"""
FastAPI Application Entry Point.

This is the main application file for the Logistics Manager Backend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from backend.app.core.config import settings
from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.dependencies import get_current_user
from backend.app.core.jwt import create_access_token
from backend.app.db.session import engine, Base
from backend.app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from fastapi import HTTPException

# Import models to ensure they are registered with Base
from backend.app.models.user import User
from backend.app.models.audit_log import AuditLog
from backend.app.models.hub import Hub  # Phase 2.1
from backend.app.models.parcel import Parcel  # Phase 2.2
from backend.app.models.fleet_vehicle import FleetVehicle  # Phase 2.3.1a (before route for FK)
from backend.app.models.fleet_route import FleetRoute  # Phase 2.3.1
from backend.app.models.hub_route_request import HubRouteRequest  # Phase 2.3
from backend.app.models.ml_route_weight import MLRouteWeight  # Phase 2.3
from backend.app.models.ml_training_data import MLRouteTrainingData  # Phase 2.3
from backend.app.models.trip import Trip  # Phase 2.4
from backend.app.models.trip_stop import TripStop  # Phase 2.4
from backend.app.models.route_request_trip_map import RouteRequestTripMap  # Phase 2.4
from backend.app.models.vehicle_lock import VehicleLock  # Phase 2.5
from backend.app.models.trip_location import TripLocation  # Phase 2.5
from backend.app.models.pricing_rule import PricingRule  # Phase 2.6
from backend.app.models.trip_charge import TripCharge  # Phase 2.6
from backend.app.models.settlement import Settlement  # Phase 2.6
from backend.app.models.ledger_entry import LedgerEntry  # Phase 2.6
from backend.app.models.dlq import DeadLetterQueue  # Phase 3
from backend.app.models.archived_trip_location import ArchivedTripLocation  # Phase 3
from backend.app.models.notification import Notification  # Phase 0.5 (Hotfix)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup/shutdown.
    
    1. Creates database tables on startup.
    2. Handles graceful shutdown (if needed).
    """
    # Create tables on startup (includes User and AuditLog)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup (optional)

# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    debug=settings.debug,
    description="A scalable FastAPI backend for logistics management",
    lifespan=lifespan,
)

# Register global exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status and application information
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.api_version,
    }


# Include API v1 router
app.include_router(api_v1_router, prefix=f"/{settings.api_version}")


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message and API documentation links
    """
    return {
        "message": "Welcome to Logistics Manager Backend API",
        "docs": "/docs",
        "health": "/health",
    }


# Authentication test endpoints (for Phase-2 validation)
@app.post("/auth/test-token", tags=["Authentication"])
async def generate_test_token(user_id: int = 1, username: str = "test_user"):
    """
    Generate a test JWT token.
    
    This endpoint is for Phase-2 validation purposes only.
    """
    token = create_access_token(data={"sub": username, "user_id": user_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
    }


@app.get("/auth/protected", tags=["Authentication"])
async def protected_route(current_user: dict = Depends(get_current_user)):
    """
    Protected route that requires valid JWT authentication.
    
    Returns 401 if token is missing or invalid.
    Returns 200 with user info if authentication succeeds.
    """
    return {
        "message": "Access granted to protected resource",
        "authenticated_user": current_user,
    }
