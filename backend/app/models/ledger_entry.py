"""
Ledger Entry database model for Phase 2.6.

Immutable double-entry accounting records.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Enum, String
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.billing_enums import LedgerEntryType


class LedgerEntry(Base):
    """
    Ledger Entry model.
    
    Immutable record of financial movement.
    Double-entry principle: Every settlement generates at least two entries (Debit Payer, Credit Payee).
    NO updates or deletions allowed.
    """
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Linkage
    settlement_id = Column(Integer, ForeignKey('settlements.id'), nullable=False, index=True)
    
    # Entry details
    entry_type = Column(Enum(LedgerEntryType), nullable=False)  # DEBIT or CREDIT
    account_owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Financials
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)
    
    # Timestamps (Immutable - no updated_at)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<LedgerEntry(id={self.id}, type='{self.entry_type.value}', amount={self.amount})>"
