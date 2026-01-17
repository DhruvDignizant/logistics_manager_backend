"""
Token Revocation System using Redis.

Implements token blacklisting to immediately invalidate JWT tokens
when users are blocked or logged out.
"""

from typing import Optional
from datetime import datetime, timedelta
from backend.app.core.redis_client import redis_client
from backend.app.core.config import settings


# Redis key prefix for blacklisted tokens
TOKEN_BLACKLIST_PREFIX = "blacklist:token:"
USER_TOKENS_PREFIX = "user:tokens:"


async def revoke_token(token: str, user_id: int) -> bool:
    """
    Revoke a specific JWT token by adding it to the blacklist.
    
    Args:
        token: The JWT token string to revoke
        user_id: User ID who owns the token
        
    Returns:
        True if successfully revoked, False otherwise
    """
    try:
        # Calculate TTL based on token expiry (tokens auto-expire anyway)
        ttl_seconds = settings.access_token_expire_minutes * 60
        
        # Add token to blacklist with TTL
        key = f"{TOKEN_BLACKLIST_PREFIX}{token}"
        await redis_client.setex(
            key,
            ttl_seconds,
            str(user_id)  # Store user_id for audit purposes
        )
        
        return True
    except Exception as e:
        print(f"Error revoking token: {e}")
        return False


async def is_token_revoked(token: str) -> bool:
    """
    Check if a token has been revoked.
    
    Args:
        token: JWT token string to check
        
    Returns:
        True if token is revoked, False otherwise
    """
    try:
        key = f"{TOKEN_BLACKLIST_PREFIX}{token}"
        exists = await redis_client.exists(key)
        return exists > 0
    except Exception as e:
        print(f"Error checking token revocation: {e}")
        # Fail-safe: If Redis is down, allow the request (security vs availability trade-off)
        # In production, you might want to fail-closed instead
        return False


async def revoke_all_user_tokens(user_id: int) -> bool:
    """
    Revoke all active tokens for a specific user.
    
    This is called when a user is blocked to immediately terminate all sessions.
    Note: This is a simplified version. In production, you'd track all active tokens
    per user in Redis.
    
    Args:
        user_id: User ID whose tokens should be revoked
        
    Returns:
        True if successful
    """
    try:
        # Mark user as having all tokens revoked
        # Any token validation will check this flag
        key = f"{USER_TOKENS_PREFIX}{user_id}:revoked"
        # Set with TTL equal to max token lifetime
        ttl_seconds = settings.access_token_expire_minutes * 60
        await redis_client.setex(key, ttl_seconds, "1")
        
        return True
    except Exception as e:
        print(f"Error revoking all tokens for user {user_id}: {e}")
        return False


async def are_user_tokens_revoked(user_id: int) -> bool:
    """
    Check if all tokens for a user have been revoked.
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if all user tokens are revoked, False otherwise
    """
    try:
        key = f"{USER_TOKENS_PREFIX}{user_id}:revoked"
        exists = await redis_client.exists(key)
        return exists > 0
    except Exception as e:
        print(f"Error checking user token revocation: {e}")
        return False


async def clear_user_token_revocation(user_id: int) -> bool:
    """
    Clear the global token revocation flag for a user.
    
    Called when a blocked user is unblocked.
    
    Args:
        user_id: User ID to clear revocation for
        
    Returns:
        True if successful
    """
    try:
        key = f"{USER_TOKENS_PREFIX}{user_id}:revoked"
        await redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Error clearing token revocation for user {user_id}: {e}")
        return False
