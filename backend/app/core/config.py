"""
Configuration settings for the Logistics Manager Backend.

This module handles application configuration using Pydantic settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Logistics Manager Backend"
    api_version: str = "v1"
    debug: bool = True
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/logistics_db"
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10
    
    # Security Configuration (JWT)
    secret_key: str = "your-secret-key-change-this-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_decode_responses: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
