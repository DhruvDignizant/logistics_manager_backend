"""
Analytics API Endpoints - Phase 2.7.

Read-only dashboard data for all roles.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.app.db.session import get_db
from backend.app.models.enums import UserRole
from backend.app.core.guards import require_role
from backend.app.services.analytics import AnalyticsService
from backend.app.schemas.analytics import (
    FleetOverviewStats, VehicleUtilization,
    HubOverviewStats, AdminSystemStats, MLPerformanceStats
)

fleet_router = APIRouter(prefix="/fleet-owner/analytics", tags=["Fleet Owner - Analytics"])
hub_router = APIRouter(prefix="/hub-owner/analytics", tags=["Hub Owner - Analytics"])
admin_router = APIRouter(prefix="/admin/analytics", tags=["Admin - Analytics"])


# --- Fleet Owner ---

@fleet_router.get("/overview", response_model=FleetOverviewStats)
async def get_fleet_analytics_overview(
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """Get high-level fleet performance stats."""
    return await AnalyticsService.get_fleet_overview(db, current_user["user_id"])


@fleet_router.get("/vehicles", response_model=List[VehicleUtilization])
async def get_vehicle_analytics(
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """Get utilization and revenue stats per vehicle."""
    return await AnalyticsService.get_vehicle_utilization(db, current_user["user_id"])


# --- Hub Owner ---

@hub_router.get("/overview", response_model=HubOverviewStats)
async def get_hub_analytics_overview(
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """Get high-level hub performance stats."""
    return await AnalyticsService.get_hub_overview(db, current_user["user_id"])


# --- Admin ---

@admin_router.get("/system", response_model=AdminSystemStats)
async def get_system_analytics(
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide operational stats."""
    return await AnalyticsService.get_admin_system_stats(db)


@admin_router.get("/ml", response_model=MLPerformanceStats)
async def get_ml_analytics(
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Get ML model performance metrics."""
    return await AnalyticsService.get_ml_performance(db)
