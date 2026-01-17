"""
Authentication API endpoints.

Provides register, login, and user info endpoints for Flutter and other clients.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.enums import UserRole
from backend.app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from backend.app.core.security import get_password_hash, verify_password
from backend.app.core.jwt import create_access_token
from backend.app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    Enforces Phase-2A v1.1 Rules:
    - ADMIN role cannot be created via API.
    - DRIVER role MUST accept a valid fleet_owner_id.
    - OWNER roles (HUB/FLEET) MUST NOT have a fleet_owner_id.
    """
    # 1. Block ADMIN registration
    if user_data.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot be registered via API"
        )

    # 2. Check if username or email already exists
    result = await db.execute(
        select(User).where(
            or_(User.username == user_data.username, User.email == user_data.email)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
            
    # 3. Hierarchy Validation (v1.1)
    if user_data.role == UserRole.DRIVER:
        if not user_data.fleet_owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Drivers must be assigned to a Fleet Owner (missing fleet_owner_id)"
            )
        
        # Verify Fleet Owner exists and has correct role
        fleet_owner_result = await db.execute(
            select(User).where(User.id == user_data.fleet_owner_id)
        )
        fleet_owner = fleet_owner_result.scalar_one_or_none()
        
        if not fleet_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fleet Owner not found"
            )
        
        if fleet_owner.role != UserRole.FLEET_OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a Fleet Owner"
            )
            
    elif user_data.role in [UserRole.HUB_OWNER, UserRole.FLEET_OWNER]:
        if user_data.fleet_owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user_data.role.value} cannot have a fleet_owner_id"
            )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        fleet_owner_id=user_data.fleet_owner_id,
        is_active=True,
        is_superuser=False
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate JWT token with role and fleet_owner_id (if applicable)
    jwt_payload = {
        "sub": new_user.username,
        "user_id": new_user.id,
        "role": new_user.role.value,
        "fleet_owner_id": new_user.fleet_owner_id
    }
    
    access_token = create_access_token(data=jwt_payload)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        fleet_owner_id=new_user.fleet_owner_id
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user and return JWT token.
    
    Accepts username or email for login.
    Logs successful and failed login attempts for security monitoring.
    """
    from backend.app.services.audit import log_auth_event, AuditAction
    
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            or_(User.username == credentials.username, User.email == credentials.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Log failed login attempt
        await log_auth_event(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=None,
            username=credentials.username,
            metadata={"reason": "User not found"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        # Log failed login attempt
        await log_auth_event(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=user.id,
            username=user.username,
            metadata={"reason": "Invalid password"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        # Log failed login attempt for blocked user
        await log_auth_event(
            db=db,
            action=AuditAction.LOGIN_FAILED,
            user_id=user.id,
            username=user.username,
            metadata={"reason": "Account is inactive/blocked"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Generate JWT token with role and fleet_owner_id
    jwt_payload = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role.value,
        "fleet_owner_id": user.fleet_owner_id
    }
    
    access_token = create_access_token(data=jwt_payload)
    
    # Log successful login
    await log_auth_event(
        db=db,
        action=AuditAction.LOGIN_SUCCESS,
        user_id=user.id,
        username=user.username
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        fleet_owner_id=user.fleet_owner_id
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    Returns detailed user info including role.
    Requires valid JWT token in Authorization header.
    
    Args:
        current_user: Decoded JWT payload from auth dependency
        db: Database session
        
    Returns:
        UserResponse with complete user information
        
    Raises:
        404: If user not found in database
    """
    user_id = current_user.get("user_id")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)
