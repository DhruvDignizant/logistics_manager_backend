"""
Parcel Management API Endpoints - Phase 2.2.

Allows Hub Owners to manage parcels within their hubs with strict ownership enforcement.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.session import get_db
from backend.app.models.parcel import Parcel
from backend.app.models.hub import Hub
from backend.app.models.parcel_enums import ParcelStatus
from backend.app.schemas.parcel import ParcelCreate, ParcelUpdate, ParcelResponse, ParcelListResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.core.dependencies import get_current_user
from backend.app.models.enums import UserRole
from backend.app.services.audit import log_event, AuditAction

router = APIRouter(prefix="/hub-owner", tags=["Hub Owner - Parcels"])
ownership_guard = OwnershipGuard()


@router.post("/hubs/{hub_id}/parcels", response_model=ParcelResponse, status_code=status.HTTP_201_CREATED)
async def create_parcel(
    hub_id: int = Path(..., description="Hub ID"),
    parcel_data: ParcelCreate = ...,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new parcel in a specific hub (Hub Owner only).
    
    Validates:
    - Hub exists and is active
    - Hub belongs to current user (ownership)
    - Reference code is unique
    """
    # Get hub and validate ownership
    result = await db.execute(
        select(Hub).where(Hub.id == hub_id, Hub.is_active == True)
    )
    hub = result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found or inactive"
        )
    
    # Enforce hub ownership
    ownership_guard.enforce(hub.hub_owner_id, current_user, "hub")
    
    # Check if reference code already exists
    ref_check = await db.execute(
        select(Parcel).where(Parcel.reference_code == parcel_data.reference_code)
    )
    if ref_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parcel with reference code '{parcel_data.reference_code}' already exists"
        )
    
    # Create parcel
    new_parcel = Parcel(
        hub_id=hub_id,
        hub_owner_id=current_user["user_id"],
        reference_code=parcel_data.reference_code,
        description=parcel_data.description,
        weight_kg=parcel_data.weight_kg,
        length_cm=parcel_data.length_cm,
        width_cm=parcel_data.width_cm,
        height_cm=parcel_data.height_cm,
        quantity=parcel_data.quantity,
        delivery_due_date=parcel_data.delivery_due_date,
        status=ParcelStatus.PENDING,
        is_active=True
    )
    
    db.add(new_parcel)
    await db.commit()
    await db.refresh(new_parcel)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.PARCEL_CREATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "parcel_id": new_parcel.id,
            "reference_code": new_parcel.reference_code,
            "hub_id": hub_id,
            "weight_kg": new_parcel.weight_kg
        }
    )
    
    return ParcelResponse.model_validate(new_parcel)


@router.get("/hubs/{hub_id}/parcels", response_model=ParcelListResponse)
async def list_hub_parcels(
    hub_id: int = Path(..., description="Hub ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all parcels in a specific hub (Hub Owner only).
    
    Only shows parcels from hubs owned by the current user.
    """
    # Get hub and validate ownership
    result = await db.execute(
        select(Hub).where(Hub.id == hub_id)
    )
    hub = result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found"
        )
    
    # Enforce hub ownership
    ownership_guard.enforce(hub.hub_owner_id, current_user, "hub")
    
    # Get total count
    count_query = select(func.count(Parcel.id)).where(
        Parcel.hub_id == hub_id,
        Parcel.is_active == True
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated parcels
    offset = (page - 1) * page_size
    query = select(Parcel).where(
        Parcel.hub_id == hub_id,
        Parcel.is_active == True
    ).order_by(Parcel.created_at.desc()).offset(offset).limit(page_size)
    
    parcel_result = await db.execute(query)
    parcels = parcel_result.scalars().all()
    
    return ParcelListResponse(
        parcels=[ParcelResponse.model_validate(p) for p in parcels],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/parcels/{parcel_id}", response_model=ParcelResponse)
async def get_parcel(
    parcel_id: int = Path(..., description="Parcel ID"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific parcel (Hub Owner only).
    
    Ownership is enforced - can only view own parcels.
    """
    result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id, Parcel.is_active == True)
    )
    parcel = result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(parcel.hub_owner_id, current_user, "parcel")
    
    return ParcelResponse.model_validate(parcel)


@router.patch("/parcels/{parcel_id}", response_model=ParcelResponse)
async def update_parcel(
    parcel_id: int = Path(..., description="Parcel ID"),
    parcel_data: ParcelUpdate = ...,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Update parcel details (Hub Owner only).
    
    Can only update own parcels (ownership enforced).
    Cannot update cancelled parcels.
    """
    result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id, Parcel.is_active == True)
    )
    parcel = result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(parcel.hub_owner_id, current_user, "parcel")
    
    # Prevent updating cancelled parcels
    if parcel.status == ParcelStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update cancelled parcel"
        )
    
    # Update fields (only if provided)
    update_data = parcel_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(parcel, field, value)
    
    await db.commit()
    await db.refresh(parcel)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.PARCEL_UPDATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "parcel_id": parcel.id,
            "reference_code": parcel.reference_code,
            "updated_fields": list(update_data.keys())
        }
    )
    
    return ParcelResponse.model_validate(parcel)


@router.patch("/parcels/{parcel_id}/cancel", response_model=ParcelResponse)
async def cancel_parcel(
    parcel_id: int = Path(..., description="Parcel ID"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a parcel (status-based soft cancel) - Hub Owner only.
    
    Can only cancel own parcels (ownership enforced).
    """
    result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id, Parcel.is_active == True)
    )
    parcel = result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(parcel.hub_owner_id, current_user, "parcel")
    
    # Check if already cancelled
    if parcel.status == ParcelStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parcel is already cancelled"
        )
    
    # Cancel parcel (status update)
    parcel.status = ParcelStatus.CANCELLED
    await db.commit()
    await db.refresh(parcel)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.PARCEL_CANCELLED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "parcel_id": parcel.id,
            "reference_code": parcel.reference_code,
            "previous_status": parcel.status.value
        }
    )
    
    return ParcelResponse.model_validate(parcel)
