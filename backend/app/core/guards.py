"""
Security guards for role-based and ownership-based access control.

Provides decorators and dependencies for protecting endpoints.
"""

from typing import List, Callable, Optional
from functools import wraps
from fastapi import Depends, HTTPException, status
from backend.app.models.enums import UserRole
from backend.app.core.dependencies import get_current_user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
            ...
    
    Args:
        allowed_roles: List of UserRole enums that are allowed to access the endpoint
        
    Returns:
        FastAPI dependency function that validates user role
        
    Raises:
        HTTPException 403 if user role is not in allowed_roles
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role_str = current_user.get("role")
        
        if not user_role_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role information missing from token"
            )
        
        # Convert string role to UserRole enum
        try:
            user_role = UserRole(user_role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid role in token"
            )
        
        # Check if user role is in allowed roles
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}"
            )
        
        return current_user
    
    return role_checker


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency for admin-only endpoints.
    
    Usage:
        @router.post("/admin/users/{user_id}/block")
        async def block_user(
            user_id: int,
            admin: dict = Depends(require_admin)
        ):
            ...
    
    Args:
        current_user: Authenticated user from JWT
        
    Returns:
        User payload if admin, raises 403 otherwise
    """
    user_role_str = current_user.get("role")
    
    if user_role_str != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


def require_fleet_owner(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency for Fleet Owner-only endpoints.
    
    Args:
        current_user: Authenticated user from JWT
        
    Returns:
        User payload if Fleet Owner, raises 403 otherwise
    """
    user_role_str = current_user.get("role")
    
    if user_role_str != UserRole.FLEET_OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fleet Owner access required"
        )
    
    return current_user


def verify_ownership(
    resource_owner_id: int,
    current_user: dict = Depends(get_current_user)
) -> bool:
    """
    Verify that the current user owns the resource.
    
    For Fleet Owners: user_id must match resource_owner_id
    For Admins: always allowed
    For Drivers: must belong to the fleet owner (fleet_owner_id must match)
    
    Usage:
        # In endpoint function
        if not verify_ownership(driver.fleet_owner_id, current_user):
            raise HTTPException(403, "Access denied")
    
    Args:
        resource_owner_id: The owner ID of the resource being accessed
        current_user: Authenticated user from JWT
        
    Returns:
        True if user has ownership access, False otherwise
    """
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    
    # Admins can access everything
    if user_role == UserRole.ADMIN.value:
        return True
    
    # Fleet Owners can only access their own resources
    if user_role == UserRole.FLEET_OWNER.value:
        return user_id == resource_owner_id
    
    # Drivers can only access resources belonging to their fleet owner
    if user_role == UserRole.DRIVER.value:
        fleet_owner_id = current_user.get("fleet_owner_id")
        return fleet_owner_id == resource_owner_id
    
    # For other roles (HUB_OWNER), check direct ownership
    return user_id == resource_owner_id


class OwnershipGuard:
    """
    Class-based ownership guard for validating multi-tenant access.
    
    Usage:
        ownership_guard = OwnershipGuard()
        
        @router.get("/drivers/{driver_id}")
        async def get_driver(
            driver_id: int,
            current_user: dict = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            driver = await get_driver_from_db(driver_id, db)
            ownership_guard.enforce(driver.fleet_owner_id, current_user)
            return driver
    """
    
    def enforce(
        self,
        resource_owner_id: int,
        current_user: dict,
        resource_name: str = "resource"
    ):
        """
        Enforce ownership validation, raise 403 if access denied.
        
        Args:
            resource_owner_id: Owner ID of the resource
            current_user: Current authenticated user
            resource_name: Name of resource for error message
            
        Raises:
            HTTPException 403 if ownership check fails
        """
        if not verify_ownership(resource_owner_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You do not have permission to access this {resource_name}."
            )
    
    def filter_by_ownership(
        self,
        current_user: dict
    ) -> Optional[int]:
        """
        Get the owner_id to filter database queries by.
        
        For admins: Returns None (no filtering needed)
        For Fleet Owners: Returns their user_id
        For Drivers: Returns their fleet_owner_id
        
        Usage:
            owner_filter = ownership_guard.filter_by_ownership(current_user)
            if owner_filter:
                query = query.where(User.fleet_owner_id == owner_filter)
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Owner ID to filter by, or None for admin (no filtering)
        """
        user_role = current_user.get("role")
        user_id = current_user.get("user_id")
        
        # Admins see everything
        if user_role == UserRole.ADMIN.value:
            return None
        
        # Fleet Owners filter by their own ID
        if user_role == UserRole.FLEET_OWNER.value:
            return user_id
        
        # Drivers filter by their fleet owner's ID
        if user_role == UserRole.DRIVER.value:
            return current_user.get("fleet_owner_id")
        
        # HUB_OWNER filters by their own ID
        return user_id
