"""
Integration tests for Authentication Flow (Phase-2A v1.1).

Verifies Register -> Login -> Me flow with Hierarchy Rules.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.session import get_db, Base
from backend.app.models.enums import UserRole

# Import all models to ensure they're registered with Base
from backend.app.models.user import User
from backend.app.models.audit_log import AuditLog
from backend.app.models.hub import Hub
from backend.app.models.parcel import Parcel
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.fleet_route import FleetRoute
from backend.app.models.hub_route_request import HubRouteRequest
from backend.app.models.ml_route_weight import MLRouteWeight
from backend.app.models.ml_training_data import MLRouteTrainingData
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.models.route_request_trip_map import RouteRequestTripMap
from backend.app.models.vehicle_lock import VehicleLock
from backend.app.models.trip_location import TripLocation
from backend.app.models.pricing_rule import PricingRule
from backend.app.models.trip_charge import TripCharge
from backend.app.models.settlement import Settlement
from backend.app.models.ledger_entry import LedgerEntry
from backend.app.models.dlq import DeadLetterQueue
from backend.app.models.archived_trip_location import ArchivedTripLocation
from backend.app.models.notification import Notification

# 1. Setup In-Memory Test Database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Enable foreign keys for SQLite
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

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client():
    """Async client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# 2. Test Cases (v1.1 Rules)

@pytest.mark.asyncio
async def test_admin_registration_blocked(client):
    """
    Rule 1: ADMIN role cannot be created via API.
    """
    payload = {
        "email": "admin@test.com",
        "username": "admin",
        "password": "password123",
        "role": "ADMIN"
    }
    response = await client.post("/v1/auth/register", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert "Admin users cannot be registered" in data["message"]


@pytest.mark.asyncio
async def test_fleet_owner_success(client):
    """
    Register a Fleet Owner (required for Driver tests).
    """
    payload = {
        "email": "owner@test.com",
        "username": "fleetowner",
        "password": "password123",
        "role": "FLEET_OWNER"
    }
    response = await client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "FLEET_OWNER"
    return data["user_id"]


@pytest.mark.asyncio
async def test_driver_requires_fleet_owner(client):
    """
    Rule 2: DRIVER role MUST accept a valid fleet_owner_id.
    """
    # Try without fleet_owner_id
    payload = {
        "email": "driver@test.com",
        "username": "driver1",
        "password": "password123",
        "role": "DRIVER"
    }
    response = await client.post("/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "missing fleet_owner_id" in response.json()["message"]


@pytest.mark.asyncio
async def test_driver_registration_success(client):
    """
    Rule 2 Success Case: Driver registers with valid fleet_owner_id.
    """
    # 1. Create Fleet Owner first
    owner_id = await test_fleet_owner_success(client)
    
    # 2. Register Driver
    payload = {
        "email": "driver_success@test.com",
        "username": "driver_ok",
        "password": "password123",
        "role": "DRIVER",
        "fleet_owner_id": owner_id
    }
    response = await client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "DRIVER"
    assert data["fleet_owner_id"] == owner_id
    
    # 3. Verify /me endpoint
    token = data["access_token"]
    response = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["fleet_owner_id"] == owner_id


@pytest.mark.asyncio
async def test_owner_cannot_have_parent(client):
    """
    Rule 3: OWNER roles (HUB/FLEET) MUST NOT have a fleet_owner_id.
    """
    # Create potential parent
    owner_id = await test_fleet_owner_success(client)
    
    # Try to register another owner WITH parent
    payload = {
        "email": "subowner@test.com",
        "username": "subowner",
        "password": "password123",
        "role": "HUB_OWNER",
        "fleet_owner_id": owner_id
    }
    response = await client.post("/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "cannot have a fleet_owner_id" in response.json()["message"]
