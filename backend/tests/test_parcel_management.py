"""
Integration tests for Phase 2.2 - Parcel Management.

Tests parcel CRUD operations, hub ownership validation, and access control.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from datetime import date, timedelta

from backend.app.main import app
from backend.app.db.session import get_db, Base
from backend.app.models.enums import UserRole

# Setup In-Memory Test Database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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
    """Create tables before tests and drop after."""
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

@pytest.fixture
async def hub_owner_with_hub(client):
    """Create hub owner and a hub, return token and IDs."""
    # Register hub owner
    register_response = await client.post("/v1/auth/register", json={
        "email": "hubowner@test.com",
        "username": "hubowner",
        "password": "password123",
        "role": "HUB_OWNER"
    })
    token = register_response.json()["access_token"]
    user_id = register_response.json()["user_id"]
    
    # Create hub
    hub_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Test Hub",
            "address": "123 Test St",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "pincode": "400001"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    hub_id = hub_response.json()["id"]
    
    return token, user_id, hub_id

@pytest.fixture
async def hub_owner2_with_hub(client):
    """Create second hub owner with hub for cross-tenant tests."""
    register_response = await client.post("/v1/auth/register", json={
        "email": "hubowner2@test.com",
        "username": "hubowner2",
        "password": "password123",
        "role": "HUB_OWNER"
    })
    token = register_response.json()["access_token"]
    
    hub_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Hub 2",
            "address": "456 Test St",
            "city": "Delhi",
            "state": "Delhi",
            "country": "India",
            "pincode": "110001"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    hub_id = hub_response.json()["id"]
    
    return token, hub_id


# TEST 1: Create Parcel
@pytest.mark.asyncio
async def test_create_parcel_success(client, hub_owner_with_hub):
    """Hub Owner can create a parcel in their hub."""
    token, user_id, hub_id = hub_owner_with_hub
    
    parcel_data = {
        "reference_code": "PKG001",
        "description": "Test Package",
        "weight_kg": 5.5,
        "length_cm": 30.0,
        "width_cm": 20.0,
        "height_cm": 15.0,
        "quantity": 2,
        "delivery_due_date": str(date.today() + timedelta(days=7))
    }
    
    response = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json=parcel_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["reference_code"] == "PKG001"
    assert data["hub_id"] == hub_id
    assert data["hub_owner_id"] == user_id
    assert data["status"] == "PENDING"
    assert data["is_active"] == True


# TEST 2: Cannot Create Parcel in Inactive Hub
@pytest.mark.asyncio
async def test_cannot_create_parcel_in_inactive_hub(client, hub_owner_with_hub):
    """Cannot create parcel in deactivated hub."""
    token, user_id, hub_id = hub_owner_with_hub
    
    # Deactivate hub
    await client.patch(
        f"/v1/hub-owner/hubs/{hub_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Try to create parcel
    response = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json={
            "reference_code": "PKG002",
            "description": "Test",
            "weight_kg": 1.0,
            "length_cm": 10.0,
            "width_cm": 10.0,
            "height_cm": 10.0,
            "quantity": 1,
            "delivery_due_date": str(date.today() + timedelta(days=7))
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert "inactive" in response.json()["message"].lower()


# TEST 3: List Hub Parcels
@pytest.mark.asyncio
async def test_list_hub_parcels(client, hub_owner_with_hub):
    """Hub Owner can list parcels in their hub."""
    token, user_id, hub_id = hub_owner_with_hub
    
    # Create 2 parcels
    for i in range(2):
        await client.post(
            f"/v1/hub-owner/hubs/{hub_id}/parcels",
            json={
                "reference_code": f"PKG00{i+1}",
                "description": f"Package {i+1}",
                "weight_kg": 1.0,
                "length_cm": 10.0,
                "width_cm": 10.0,
                "height_cm": 10.0,
                "quantity": 1,
                "delivery_due_date": str(date.today() + timedelta(days=7))
            },
            headers={"Authorization": f"Bearer {token}"}
        )
    
    # List parcels
    response = await client.get(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["parcels"]) == 2


# TEST 4: Cannot Access Other Owner's Hub Parcels
@pytest.mark.asyncio
async def test_cannot_access_other_owners_parcels(client, hub_owner_with_hub, hub_owner2_with_hub):
    """Hub Owner cannot access another owner's hub parcels."""
    token1, user_id1, hub_id1 = hub_owner_with_hub
    token2, hub_id2 = hub_owner2_with_hub
    
    # Owner 2 tries to list Owner 1's hub parcels
    response = await client.get(
        f"/v1/hub-owner/hubs/{hub_id1}/parcels",
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    assert response.status_code == 403


# TEST 5: Update Parcel
@pytest.mark.asyncio
async def test_update_parcel(client, hub_owner_with_hub):
    """Hub Owner can update their parcel."""
    token, user_id, hub_id = hub_owner_with_hub
    
    # Create parcel
    create_response = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json={
            "reference_code": "PKG001",
            "description": "Old Description",
            "weight_kg": 5.0,
            "length_cm": 30.0,
            "width_cm": 20.0,
            "height_cm": 15.0,
            "quantity": 1,
            "delivery_due_date": str(date.today() + timedelta(days=7))
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    parcel_id = create_response.json()["id"]
    
    # Update parcel
    update_response = await client.patch(
        f"/v1/hub-owner/parcels/{parcel_id}",
        json={"description": "Updated Description", "weight_kg": 6.0},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["description"] == "Updated Description"
    assert data["weight_kg"] == 6.0


# TEST 6: Cannot Update Cancelled Parcel
@pytest.mark.asyncio
async def test_cannot_update_cancelled_parcel(client, hub_owner_with_hub):
    """Cannot update a cancelled parcel."""
    token, user_id, hub_id = hub_owner_with_hub
      
    # Create and cancel parcel
    create_response = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json={
            "reference_code": "PKG001",
            "description": "Test",
            "weight_kg": 1.0,
            "length_cm": 10.0,
            "width_cm": 10.0,
            "height_cm": 10.0,
            "quantity": 1,
            "delivery_due_date": str(date.today() + timedelta(days=7))
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    parcel_id = create_response.json()["id"]
    
    # Cancel parcel
    await client.patch(
        f"/v1/hub-owner/parcels/{parcel_id}/cancel",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Try to update
    response = await client.patch(
        f"/v1/hub-owner/parcels/{parcel_id}",
        json={"description": "Try to update"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert "cancelled" in response.json()["message"].lower()


# TEST 7: Cancel Parcel
@pytest.mark.asyncio
async def test_cancel_parcel(client, hub_owner_with_hub):
    """Hub Owner can cancel their parcel."""
    token, user_id, hub_id = hub_owner_with_hub
    
    # Create parcel
    create_response = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json={
            "reference_code": "PKG001",
            "description": "Test",
            "weight_kg": 1.0,
            "length_cm": 10.0,
            "width_cm": 10.0,
            "height_cm": 10.0,
            "quantity": 1,
            "delivery_due_date": str(date.today() + timedelta(days=7))
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    parcel_id = create_response.json()["id"]
    
    # Cancel parcel
    cancel_response = await client.patch(
        f"/v1/hub-owner/parcels/{parcel_id}/cancel",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert cancel_response.status_code == 200
    data = cancel_response.json()
    assert data["status"] == "CANCELLED"


# TEST 8: Unique Reference Code
@pytest.mark.asyncio
async def test_unique_reference_code(client, hub_owner_with_hub):
    """Reference code must be unique across all parcels."""
    token, user_id, hub_id = hub_owner_with_hub
    
    parcel_data = {
        "reference_code": "PKG001",
        "description": "Test",
        "weight_kg": 1.0,
        "length_cm": 10.0,
        "width_cm": 10.0,
        "height_cm": 10.0,
        "quantity": 1,
        "delivery_due_date": str(date.today() + timedelta(days=7))
    }
    
    # Create first parcel
    response1 = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json=parcel_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 201
    
    # Try to create second parcel with same reference code
    response2 = await client.post(
        f"/v1/hub-owner/hubs/{hub_id}/parcels",
        json=parcel_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["message"].lower()
