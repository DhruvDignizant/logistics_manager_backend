"""
JWT token utilities for authentication.

This module provides functions for encoding and decoding JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from backend.app.core.config import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data payload to encode in the token (should include: sub, user_id, role)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
        
    Example payload:
        {
            "sub": "username",
            "user_id": 123,
            "role": "DRIVER",
            "exp": 1234567890
        }
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload if valid (includes: sub, user_id, role, exp), None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
