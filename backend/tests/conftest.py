"""
Centralized Test Configuration.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

from backend.app.main import app
from backend.app.db.session import get_db, Base
from backend.app.core.redis_client import get_redis
import backend.app.core.redis_client as redis_client_module

# Setup In-Memory Test Database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Event handler to enable foreign keys for SQLite
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite."""
    if 'sqlite' in str(type(dbapi_conn)):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Shared Database Session (Session Scope)
@pytest.fixture(scope="session")
async def db_session_factory():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield TestingSessionLocal
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Mock Redis for reliability in CI/CD
class MockRedis:
    def __init__(self):
        self.store = {}
        self._closed = False
    
    async def ping(self):
        if self._closed:
            return False
        return True
    
    async def get(self, key):
        if self._closed:
            return None
        return self.store.get(key)
        
    async def set(self, key, value, ex=None):
        if self._closed:
            return False
        self.store[key] = value
        return True
    
    async def delete(self, key):
        if self._closed:
            return 0
        if key in self.store:
            del self.store[key]
            return 1
        return 0
    
    async def exists(self, key):
        if self._closed:
            return 0
        return 1 if key in self.store else 0
        
    async def flushdb(self):
        if not self._closed:
            self.store = {}
        
    async def aclose(self):
        self._closed = True
        self.store = {}

# Redis Fixture (Session Scope)
@pytest.fixture(scope="session")
async def redis_client_session():
    return MockRedis()

@pytest.fixture(scope="session", autouse=True)
def apply_overrides(redis_client_session):
    """Apply overrides once for the session.
    Global override is safer here than per-test override to avoid app state flux.
    """
    
    # Patch the global redis client used by Middleware
    original_client = redis_client_module.redis_client
    redis_client_module.redis_client = redis_client_session
    
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    async def override_get_redis():
        return redis_client_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    yield
    
    # Restore and clear
    app.dependency_overrides = {}
    redis_client_module.redis_client = original_client

@pytest.fixture(autouse=True)
async def setup_database(redis_client_session):
    """Create tables before each test function and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await redis_client_session.flushdb()
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client():
    """Async client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# Shared session for fixture data creation
@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
