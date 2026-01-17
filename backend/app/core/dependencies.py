"""
Authentication dependencies for FastAPI.

This module provides dependencies for protecting routes with JWT authentication.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.jwt import decode_access_token

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency for JWT authentication.
    
    Validates the JWT token and returns the decoded payload.
    Raises 401 if token is missing or invalid.
    
    Args:
        credentials: HTTP Bearer token from request header
        
    Returns:
        Decoded token payload containing user information
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload
