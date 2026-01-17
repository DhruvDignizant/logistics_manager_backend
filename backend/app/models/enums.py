"""
User roles enumeration.

Defines the role types for the logistics management system.
"""

import enum


class UserRole(str, enum.Enum):
    """
    User role enumeration.
    
    Roles:
        ADMIN: Supreme user with system-level access
        HUB_OWNER: Owns and manages hubs
        FLEET_OWNER: Owns and manages vehicles/fleets
        DRIVER: Assigned to fleets and trips (default role)
    """
    ADMIN = "ADMIN"
    HUB_OWNER = "HUB_OWNER"
    FLEET_OWNER = "FLEET_OWNER"
    DRIVER = "DRIVER"
