"""
Dead Letter Queue (DLQ) Model for Phase 3.

Stores failed async tasks for retry or audit.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from sqlalchemy.sql import func
from backend.app.db.session import Base
import enum


class DLQStatus(str, enum.Enum):
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    PROCESSED = "PROCESSED"
    ARCHIVED = "ARCHIVED"  # Gave up


class DeadLetterQueue(Base):
    """
    Dead Letter Queue table.
    Captures failed background tasks.
    """
    __tablename__ = "dead_letter_queue"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    task_name = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)  # Task arguments
    
    status = Column(Enum(DLQStatus), default=DLQStatus.FAILED, nullable=False, index=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<DLQ(id={self.id}, task='{self.task_name}', status='{self.status}')>"
