"""
Notification Service - Phase 0.5 Hotfix.

Handles creation and state management of notifications.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.app.models.notification import Notification, NotificationType
from backend.app.models.user import User
from backend.app.models.enums import UserRole


class NotificationService:
    
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create a single notification."""
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            metadata_payload=metadata
        )
        db.add(notif)
        await db.flush() # Caller commits usually
        return notif

    @staticmethod
    async def broadcast(
        db: AsyncSession,
        title: str,
        message: str,
        role: Optional[UserRole] = None,
        type: NotificationType = NotificationType.INFO
    ) -> int:
        """Broadcast notification to all users or filtered by role."""
        
        # 1. Select Users
        query = select(User.id)
        if role:
            query = query.where(User.role == role)
            
        result = await db.execute(query)
        user_ids = result.scalars().all()
        
        # 2. Bulk Create (using individual objects for simplicity in this hotfix, 
        # or bulk_insert_mappings for performance if thousands)
        # For hotfix speed/safety with ORM, objects loop is fine for <1000 users.
        # If scale needed, use insert().
        
        notifications = [
            Notification(
                user_id=uid,
                title=title,
                message=message,
                type=type
            )
            for uid in user_ids
        ]
        
        if notifications:
            db.add_all(notifications)
            
        return len(notifications)

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read."""
        stmt = update(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).values(
            is_read=True,
            read_at=datetime.utcnow()
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int) -> int:
        """Mark all notifications for user as read."""
        stmt = update(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).values(
            is_read=True,
            read_at=datetime.utcnow()
        )
        result = await db.execute(stmt)
        return result.rowcount
