"""
Admin Operations API Endpoints - Phase 3.

Endpoints for managing system reliability and maintenance.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from datetime import datetime, timedelta

from backend.app.db.session import get_db
from backend.app.models.dlq import DeadLetterQueue, DLQStatus
from backend.app.models.trip_location import TripLocation
from backend.app.models.archived_trip_location import ArchivedTripLocation
from backend.app.models.enums import UserRole
from backend.app.core.guards import require_role
from backend.app.services.cache import CacheService
from backend.app.services.audit import log_event, AuditAction

router = APIRouter(prefix="/admin/ops", tags=["Admin - Ops"])


@router.post("/dlq/{dlq_id}/retry")
async def retry_dlq_item(
    dlq_id: int = Path(..., description="DLQ Item ID"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry a failed task from the Dead Letter Queue.
    (Placeholder: meaningful retry logic depends on specific task handlers)
    """
    result = await db.execute(select(DeadLetterQueue).where(DeadLetterQueue.id == dlq_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="DLQ item not found")
        
    # Logic to actually retry would parse 'task_name' and dispatch.
    # For MVP, we mark as RETRYING.
    
    item.status = DLQStatus.RETRYING
    item.retry_count += 1
    item.last_retry_at = datetime.utcnow()
    
    await db.commit()
    return {"message": f"Task {item.task_name} marked for retry"}


@router.post("/trigger-archival")
async def trigger_data_archival(
    days_to_keep: int = 30,
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger archival of old Trip Locations > N days.
    Moves data from hot table to archive table.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Select old rows
    stmt = select(TripLocation).where(TripLocation.recorded_at < cutoff_date).limit(1000)
    result = await db.execute(stmt)
    rows_to_archive = result.scalars().all()
    
    count = 0
    if rows_to_archive:
        # Bulk Insert to Archive
        archive_data = [
            {
                "original_id": r.id,
                "trip_id": r.trip_id,
                "driver_id": r.driver_id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "accuracy_meters": r.accuracy_meters,
                "recorded_at": r.recorded_at,
                "archived_at": datetime.utcnow()
            }
            for r in rows_to_archive
        ]
        
        await db.execute(insert(ArchivedTripLocation), archive_data)
        
        # Delete from Hot Table
        ids_to_delete = [r.id for r in rows_to_archive]
        await db.execute(delete(TripLocation).where(TripLocation.id.in_(ids_to_delete)))
        
        await db.commit()
        count = len(rows_to_archive)
        
    return {"message": "Archival job completed", "rows_archived": count}


@router.post("/clear-cache")
async def clear_system_cache(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Clear the internal cache."""
    await CacheService.clear()
    return {"message": "Cache cleared successfully"}
