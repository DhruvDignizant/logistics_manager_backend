"""
Parcel Status Enumeration for Phase 2.2.
"""

import enum


class ParcelStatus(str, enum.Enum):
    """
    Parcel status enumeration.
    
    Status flow:
        PENDING → IN_TRANSIT → DELIVERED
        Any status can transition to CANCELLED
    """
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
