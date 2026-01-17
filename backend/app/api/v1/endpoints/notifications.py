"""
Notification API Endpoints - Phase 0.5 Hotfix.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from backend.app.db.session import get_db
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.enums import UserRole
from backend.app.core.guards import require_role, get_current_user
from backend.app.services.notification_service import NotificationService
from backend.app.schemas.notification import NotificationResponse, BroadcastRequest

router = APIRouter(prefix="/notifications", tags=["Notifications"])
admin_router = APIRouter(prefix="/admin/notifications", tags=["Admin - Notifications"])


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List current user's notifications."""
    query = select(Notification).where(Notification.user_id == current_user["user_id"])
    
    if unread_only:
        query = query.where(Notification.is_read == False)
        
    query = query.order_by(desc(Notification.created_at)).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int = Path(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a specific notification as read."""
    success = await NotificationService.mark_read(db, notification_id, current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await db.commit()
    return {"status": "success"}


@router.patch("/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read."""
    count = await NotificationService.mark_all_read(db, current_user["user_id"])
    await db.commit()
    return {"status": "success", "count": count}


# --- Admin Broadcast ---

@admin_router.post("/broadcast")
async def broadcast_notification(
    req: BroadcastRequest,
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Send a notification to many users."""
    role_enum = None
    if req.role_filter:
        try:
            role_enum = UserRole(req.role_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role filter")
            
    count = await NotificationService.broadcast(
        db, req.title, req.message, role_enum, req.type
    )
    await db.commit()
    return {"status": "success", "recipients": count}
