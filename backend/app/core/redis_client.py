"""
Redis client initialization and connection management.

This module provides Redis client setup for caching and session management.
"""

import redis.asyncio as redis
from backend.app.core.config import settings


# Create async Redis client
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=settings.redis_decode_responses,
)


async def get_redis():
    """
    Get Redis client instance.
    
    This can be used as a FastAPI dependency if needed.
    """
    return redis_client


async def ping_redis() -> bool:
    """
    Test Redis connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        return await redis_client.ping()
    except Exception:
        return False
