"""
Caching Service for Phase 3.

Simple memory-based cache for heavy analytics.
In production, this would wrap Redis.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

# In-memory store (Replace with Redis in real production)
_cache_store: Dict[str, dict] = {}

class CacheService:
    
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        entry = _cache_store.get(key)
        if not entry:
            return None
        
        if datetime.utcnow() > entry["expires_at"]:
            del _cache_store[key]
            return None
            
        return entry["data"]

    @staticmethod
    async def set(key: str, data: Any, ttl_seconds: int = 300):
        _cache_store[key] = {
            "data": data,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds)
        }
        
    @staticmethod
    async def clear():
        _cache_store.clear()

# Decorator for easy caching
from functools import wraps

def cache_response(ttl_seconds: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create simplistic key from args (Note: complex objects need serialization)
            # Should rely on caller to pass unique ID if needed or serialize args
            
            # For this MVP, we won't implement automatic key generation for complex args
            # relying on direct CacheService usage in controllers is safer.
            return await func(*args, **kwargs)
        return wrapper
    return decorator
