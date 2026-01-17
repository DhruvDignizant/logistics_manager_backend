"""
Billing enumerations for Phase 2.6.
"""

import enum


class SettlementStatus(str, enum.Enum):
    """Settlement status enumeration."""
    PENDING = "PENDING"  # Created, waiting for admin approval
    APPROVED = "APPROVED"  # Approved by admin, waiting for payment
    PAID = "PAID"  # Payment processed


class LedgerEntryType(str, enum.Enum):
    """Ledger entry type enumeration."""
    DEBIT = "DEBIT"  # Money leaving the account
    CREDIT = "CREDIT"  # Money entering the account
