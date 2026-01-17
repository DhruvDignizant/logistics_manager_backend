"""
Route-related enumerations for Phase 2.3.
"""

import enum


class RouteStatus(str, enum.Enum):
    """Route status enumeration."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RouteRequestStatus(str, enum.Enum):
    """
    Hub route request status.
    
    PENDING: Hub owner requested route suggestion
    ACCEPTED: Fleet owner accepted the request
    REJECTED: Fleet owner rejected the request
    """
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
