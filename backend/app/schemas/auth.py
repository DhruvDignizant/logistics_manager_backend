"""
Authentication Pydantic schemas.

Defines request and response schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from backend.app.models.enums import UserRole


class UserRegister(BaseModel):
    """
    Schema for user registration.
    
    Used by POST /auth/register endpoint.
    Default role is DRIVER (for Flutter users).
    """
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    role: Optional[UserRole] = Field(default=UserRole.DRIVER, description="User role (defaults to DRIVER)")
    fleet_owner_id: Optional[int] = Field(default=None, description="ID of fleet owner (Required for DRIVER)")


class UserLogin(BaseModel):
    """
    Schema for user login.
    
    Used by POST /auth/login endpoint.
    Supports login with either username or email.
    """
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """
    Schema for JWT token response.
    
    Returned by successful login/register operations.
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: UserRole = Field(..., description="User role")
    fleet_owner_id: Optional[int] = Field(default=None, description="Fleet Owner ID (for Drivers)")


class UserResponse(BaseModel):
    """
    Schema for user information response.
    
    Used by GET /auth/me endpoint.
    """
    id: int
    email: str
    username: str
    role: UserRole
    fleet_owner_id: Optional[int] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
