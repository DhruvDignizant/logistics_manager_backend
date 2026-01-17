"""
Database session configuration.

This module handles database engine creation and session management
using SQLAlchemy with async support for PostgreSQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base for models
Base = declarative_base()


async def get_db():
    """
    FastAPI dependency for database sessions.
    
    Yields an async database session and ensures it's properly closed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
