"""
Owner Billing API Endpoints - Phase 2.6.

Read-only financial views for Hub Owners and Fleet Owners.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend.app.db.session import get_db
from backend.app.models.trip_charge import TripCharge
from backend.app.models.settlement import Settlement
from backend.app.models.enums import UserRole
from backend.app.schemas.billing import TripChargeResponse, SettlementResponse
from backend.app.core.guards import require_role

hub_router = APIRouter(prefix="/hub-owner", tags=["Hub Owner - Billing"])
fleet_router = APIRouter(prefix="/fleet-owner", tags=["Fleet Owner - Billing"])


@hub_router.get("/charges", response_model=List[TripChargeResponse])
async def list_hub_charges(
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """List charges payable by the Hub Owner."""
    query = select(TripCharge).where(TripCharge.hub_owner_id == current_user["user_id"])
    result = await db.execute(query)
    return result.scalars().all()


@hub_router.get("/settlements", response_model=List[SettlementResponse])
async def list_hub_settlements(
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """List settlements (Payable) for the Hub Owner."""
    query = select(Settlement).where(Settlement.hub_owner_id == current_user["user_id"])
    result = await db.execute(query)
    return result.scalars().all()


@fleet_router.get("/earnings", response_model=List[TripChargeResponse])
async def list_fleet_earnings(
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """List earnings (Receivable) for the Fleet Owner."""
    query = select(TripCharge).where(TripCharge.fleet_owner_id == current_user["user_id"])
    result = await db.execute(query)
    return result.scalars().all()


@fleet_router.get("/settlements", response_model=List[SettlementResponse])
async def list_fleet_settlements(
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """List settlements (Receivable) for the Fleet Owner."""
    # Fleet owners are the payee
    query = select(Settlement).where(Settlement.fleet_owner_id == current_user["user_id"])
    result = await db.execute(query)
    return result.scalars().all()
