"""
API v1 Router.

This module aggregates all API v1 endpoints.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth

router = APIRouter()

# Include authentication endpoints
router.include_router(auth.router)

# Future domain API routes will be added here
# Example:
# from backend.app.api.v1.endpoints import fleet, hubs, trips
# router.include_router(fleet.router, prefix="/fleet", tags=["Fleet"])
# router.include_router(hubs.router, prefix="/hubs", tags=["Hubs"])
