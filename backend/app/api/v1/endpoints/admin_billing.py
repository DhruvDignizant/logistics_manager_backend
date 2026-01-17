"""
Admin Billing API Endpoints - Phase 2.6.

Handles pricing rule management and settlement workflows.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from typing import List

from backend.app.db.session import get_db
from backend.app.models.pricing_rule import PricingRule
from backend.app.models.settlement import Settlement
from backend.app.models.billing_enums import SettlementStatus
from backend.app.models.enums import UserRole
from backend.app.schemas.billing import (
    PricingRuleCreate, PricingRuleResponse, AdminSettlementActionResponse
)
from backend.app.core.guards import require_role
from backend.app.services.audit import log_event, AuditAction

router = APIRouter(prefix="/admin", tags=["Admin - Billing"])


@router.post("/pricing-rules", response_model=PricingRuleResponse)
async def create_pricing_rule(
    rule: PricingRuleCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new pricing rule.
    """
    # Deactivate currently active rules that overlap?
    # For now, we assume implicit selection by date in PricingResolver.
    # But strictly, we should check if multiple rules are active.
    # We will just insert it. Resolver picks priority.
    
    new_rule = PricingRule(
        rule_name=rule.rule_name,
        base_rate_per_km=rule.base_rate_per_km,
        weight_surcharge_per_kg=rule.weight_surcharge_per_kg,
        effective_from=rule.effective_from,
        is_active=True,
        created_by_admin_id=current_user["user_id"]
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    await log_event(
        db=db,
        action=AuditAction.PRICING_RULE_CREATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "rule_id": new_rule.id,
            "name": new_rule.rule_name
        }
    )
    
    return new_rule


@router.get("/pricing-rules", response_model=List[PricingRuleResponse])
async def list_pricing_rules(
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all pricing rules.
    """
    result = await db.execute(
        select(PricingRule).order_by(desc(PricingRule.effective_from))
    )
    return result.scalars().all()


@router.post("/settlements/{settlement_id}/approve", response_model=AdminSettlementActionResponse)
async def approve_settlement(
    settlement_id: int = Path(..., description="Settlement ID"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a PENDING settlement.
    """
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    settlement = result.scalar_one_or_none()
    
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
        
    if settlement.status != SettlementStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Settlement status is {settlement.status.value}, expected PENDING")
        
    settlement.status = SettlementStatus.APPROVED
    settlement.approved_by_admin_id = current_user["user_id"]
    settlement.approved_at = datetime.utcnow()
    settlement.updated_at = datetime.utcnow()
    
    await db.commit()
    
    await log_event(
        db=db,
        action=AuditAction.SETTLEMENT_APPROVED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={"settlement_id": settlement.id}
    )
    
    return AdminSettlementActionResponse(
        settlement_id=settlement.id,
        status=settlement.status.value,
        updated_at=settlement.updated_at
    )


@router.post("/settlements/{settlement_id}/mark-paid", response_model=AdminSettlementActionResponse)
async def mark_settlement_paid(
    settlement_id: int = Path(..., description="Settlement ID"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an APPROVED settlement as PAID.
    """
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    settlement = result.scalar_one_or_none()
    
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
        
    if settlement.status != SettlementStatus.APPROVED:
        raise HTTPException(status_code=400, detail=f"Settlement status is {settlement.status.value}, expected APPROVED")
        
    settlement.status = SettlementStatus.PAID
    settlement.paid_at = datetime.utcnow()
    settlement.updated_at = datetime.utcnow()
    
    await db.commit()
    
    await log_event(
        db=db,
        action=AuditAction.SETTLEMENT_PAID,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={"settlement_id": settlement.id}
    )
    
    return AdminSettlementActionResponse(
        settlement_id=settlement.id,
        status=settlement.status.value,
        updated_at=settlement.updated_at
    )
