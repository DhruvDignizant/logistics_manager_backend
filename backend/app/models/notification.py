"""
Notification Database Model - Phase 0.5 Hotfix.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from backend.app.db.session import Base
import enum


class NotificationType(str, enum.Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    TRIP_UPDATE = "TRIP_UPDATE"
    BILLING_UPDATE = "BILLING_UPDATE"


class Notification(Base):
    """
    In-App Notification.
    Stores messages for users.
    """
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Recipient
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Content
    type = Column(Enum(NotificationType), default=NotificationType.INFO, nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    metadata_payload = Column(JSON, nullable=True) # Renamed to avoid reserved word conflict if any
    
    # State
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user={self.user_id}, title='{self.title}')>"
