"""
Authentication dependencies for FastAPI.

This module provides dependencies for protecting routes with JWT authentication.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.jwt import decode_access_token
from backend.app.core.token_revocation import is_token_revoked, are_user_tokens_revoked
from backend.app.db.session import get_db
from backend.app.models.user import User

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    FastAPI dependency for JWT authentication with security hardening.
    
    Security checks (Phase 1):
    1. Validates JWT token signature and expiry
    2. Checks if token has been explicitly revoked
    3. Checks if all user tokens have been revoked (user blocked)
    4. Verifies user is still active in database (real-time check)
    
    Args:
        credentials: HTTP Bearer token from request header
        db: Database session for real-time user status check
        
    Returns:
        Decoded token payload containing user information
        
    Raises:
        HTTPException: 401 if authentication fails for any reason
    """
    token = credentials.credentials
    
    # 1. Decode and validate JWT
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Check if this specific token has been revoked
    if await is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Check if all user tokens have been revoked (user was blocked)
    if await are_user_tokens_revoked(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User access has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 4. Real-time database check: Verify user is still active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return payload
