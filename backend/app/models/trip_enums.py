"""
Trip-related enumerations for Phase 2.4.
"""

import enum


class TripStatus(str, enum.Enum):
    """Trip status enumeration."""
    PLANNED = "PLANNED"  # Created from accepted request, awaiting driver assignment
    PENDING = "PENDING"  # Driver assigned but not started
    IN_PROGRESS = "IN_PROGRESS"  # Driver has started
    COMPLETED = "COMPLETED"  # All stops delivered
    CANCELLED = "CANCELLED"  # Trip cancelled


class TripStopType(str, enum.Enum):
    """Trip stop type enumeration."""
    PICKUP = "PICKUP"  # Pick up parcel from hub
    DELIVERY = "DELIVERY"  # Deliver parcel to destination


class TripStopStatus(str, enum.Enum):
    """Trip stop status enumeration."""
    PENDING = "PENDING"  # Not yet visited
    COMPLETED = "COMPLETED"  # Stop completed
    SKIPPED = "SKIPPED"  # Stop skipped
