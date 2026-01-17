"""
Audit Log Database Model.

Tracks security-critical events and admin actions for compliance and security monitoring.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from backend.app.db.session import Base


class AuditLog(Base):
    """
    Audit log model for tracking security events and admin actions.
    
    Events logged:
    - USER_BLOCKED / USER_UNBLOCKED
    - USER_CREATED / USER_DELETED
    - LOGIN_SUCCESS / LOGIN_FAILED
    - TOKEN_REVOKED
    - ROLE_CHANGED (for privilege escalation detection)
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Who performed the action (None for system actions)
    actor_id = Column(Integer, index=True, nullable=True)
    actor_username = Column(String(100), nullable=True)
    
    # What action was performed
    action = Column(String(100), nullable=False, index=True)
    
    # Who was the target of the action (for user management actions)
    target_user_id = Column(Integer, index=True, nullable=True)
    target_username = Column(String(100), nullable=True)
    
    # Additional context (JSON for flexibility)
    meta_data = Column(JSON, nullable=True)
    
    # IP address for login tracking
    ip_address = Column(String(50), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', actor={self.actor_username}, target={self.target_username})>"
