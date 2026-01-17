"""
User database model.

This module defines the User SQLAlchemy model for authentication.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from backend.app.db.session import Base
from backend.app.models.enums import UserRole


class User(Base):
    """
    User model for authentication and user management.
    
    This is a minimal foundation model. Business-specific fields
    will be added in later phases.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Role-based authentication (Phase-2A)
    role = Column(Enum(UserRole), default=UserRole.DRIVER, nullable=False)
    
    # Hierarchy (Phase-2A v1.1) - Driver belongs to Fleet Owner
    fleet_owner_id = Column(Integer, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role.value}')>"
