"""
Vehicle locking service for Phase 2.5.

Manages vehicle capacity locking during trip execution.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.models.vehicle_lock import VehicleLock
from backend.app.models.trip import Trip
from backend.app.models.trip_enums import TripStatus


async def create_vehicle_lock(
    db: AsyncSession,
    vehicle_id: int,
    trip_id: int,
    driver_id: int
) -> VehicleLock:
    """
    Create a vehicle lock for a trip.
    
    Args:
        db: Database session
        vehicle_id: Vehicle to lock
        trip_id: Trip locking the vehicle
        driver_id: Driver locking the vehicle
    
    Returns:
        Created vehicle lock
    
    Raises:
        IntegrityError: If vehicle already locked
    """
    lock = VehicleLock(
        vehicle_id=vehicle_id,
        trip_id=trip_id,
        locked_by_driver_id=driver_id,
        locked_at=datetime.utcnow(),
        released_at=None
    )
    
    db.add(lock)
    await db.flush()  # Will raise IntegrityError if unique constraint violated
    
    return lock


async def is_vehicle_locked(
    db: AsyncSession,
    vehicle_id: int
) -> tuple[bool, VehicleLock | None]:
    """
    Check if a vehicle is currently locked.
    
    Args:
        db: Database session
        vehicle_id: Vehicle to check
    
    Returns:
        (is_locked: bool, lock: VehicleLock | None)
    """
    result = await db.execute(
        select(VehicleLock).where(
            VehicleLock.vehicle_id == vehicle_id,
            VehicleLock.released_at.is_(None)
        )
    )
    lock = result.scalar_one_or_none()
    
    return (lock is not None, lock)


async def release_vehicle_lock(
    db: AsyncSession,
    vehicle_id: int,
    trip_id: int
) -> bool:
    """
    Release a vehicle lock when trip completes.
    
    Args:
        db: Database session
        vehicle_id: Vehicle to unlock
        trip_id: Trip releasing the lock
    
    Returns:
        True if lock released, False if no lock found
    """
    result = await db.execute(
        select(VehicleLock).where(
            VehicleLock.vehicle_id == vehicle_id,
            VehicleLock.trip_id == trip_id,
            VehicleLock.released_at.is_(None)
        )
    )
    lock = result.scalar_one_or_none()
    
    if not lock:
        return False
    
    lock.released_at = datetime.utcnow()
    await db.flush()
    
    return True


async def count_driver_in_progress_trips(
    db: AsyncSession,
    driver_id: int
) -> int:
    """
    Count how many IN_PROGRESS trips a driver has.
    
    Should be 0 or 1 (system enforces single IN_PROGRESS trip).
    
    Args:
        db: Database session
        driver_id: Driver to check
    
    Returns:
        Count of IN_PROGRESS trips
    """
    from sqlalchemy import func as sql_func
    
    result = await db.execute(
        select(sql_func.count(Trip.id)).where(
            Trip.driver_id == driver_id,
            Trip.status == TripStatus.IN_PROGRESS
        )
    )
    return result.scalar()
