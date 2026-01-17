"""
Integration tests for Phase 2.1 - Hub Management.

Tests hub CRUD operations, ownership enforcement, and access control.
"""

import pytest
from backend.app.models.enums import UserRole

# Note: Client and DB setup are now in conftest.py


@pytest.fixture
async def hub_owner_token(client):
    """Create hub owner and return auth token."""
    response = await client.post("/v1/auth/register", json={
        "email": "hubowner1@test.com",
        "username": "hubowner1",
        "password": "password123",
        "role": "HUB_OWNER"
    })
    assert response.status_code == 201
    return response.json()["access_token"], response.json()["user_id"]

@pytest.fixture
async def hub_owner2_token(client):
    """Create second hub owner for cross-tenant tests."""
    response = await client.post("/v1/auth/register", json={
        "email": "hubowner2@test.com",
        "username": "hubowner2",
        "password": "password123",
        "role": "HUB_OWNER"
    })
    assert response.status_code == 201
    return response.json()["access_token"], response.json()["user_id"]

@pytest.fixture
async def admin_token(client, db_session):
    """Create admin user and return auth token."""
    from backend.app.models.user import User
    from backend.app.core.security import get_password_hash
    
    admin = User(
        email="admin@test.com",
        username="admin",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True
    )
    db_session.add(admin)
    await db_session.commit()
    
    # Login as admin
    response = await client.post("/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"

    })
    assert response.status_code == 200
    return response.json()["access_token"]


# TEST 1: Hub Creation
@pytest.mark.asyncio
async def test_create_hub_success(client, hub_owner_token):
    """Hub Owner can create a hub."""
    token, user_id = hub_owner_token
    
    hub_data = {
        "name": "Test Hub",
        "address": "123 Main St",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "pincode": "400001",
        "latitude": 19.0760,
        "longitude": 72.8777
    }
    
    response = await client.post(
        "/v1/hub-owner/hubs",
        json=hub_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Hub"
    assert data["hub_owner_id"] == user_id
    assert data["is_active"] == True
    assert "id" in data


# TEST 2: List Own Hubs
@pytest.mark.asyncio
async def test_list_own_hubs(client, hub_owner_token):
    """Hub Owner can list only their own hubs."""
    token, user_id = hub_owner_token
    
    # Create 2 hubs
    for i in range(2):
        await client.post(
            "/v1/hub-owner/hubs",
            json={
                "name": f"Hub {i+1}",
                "address": f"{i+1} Test St",
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "pincode": "110001"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
    
    # List hubs
    response = await client.get(
        "/v1/hub-owner/hubs",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["hubs"]) == 2
    # All hubs should belong to this owner
    for hub in data["hubs"]:
        assert hub["hub_owner_id"] == user_id


# TEST 3:Ownership Enforcement - Cannot View Other Owner's Hub
@pytest.mark.asyncio
async def test_cannot_view_other_owners_hub(client, hub_owner_token, hub_owner2_token):
    """Hub Owner cannot view another Hub Owner's hub."""
    token1, user_id1 = hub_owner_token
    token2, user_id2 = hub_owner2_token
    
    # Owner 1 creates a hub
    create_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Owner1 Hub",
            "address": "100 Private St",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "pincode": "560001"
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    hub_id = create_response.json()["id"]
    
    # Owner 2 tries to view Owner 1's hub
    response = await client.get(
        f"/v1/hub-owner/hubs/{hub_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    # Should get 403 Forbidden (ownership guard)
    assert response.status_code == 403


# TEST 4: Update Hub
@pytest.mark.asyncio
async def test_update_hub(client, hub_owner_token):
    """Hub Owner can update their own hub."""
    token, user_id = hub_owner_token
    
    # Create hub
    create_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Old Name",
            "address": "Old Address",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "country": "India",
            "pincode": "600001"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    hub_id = create_response.json()["id"]
    
    # Update hub
    update_response = await client.patch(
        f"/v1/hub-owner/hubs/{hub_id}",
        json={"name": "New Name", "address": "New Address"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "New Name"
    assert data["address"] == "New Address"
    assert data["city"] == "Chennai"  # Unchanged


# TEST 5: Cannot Update Other Owner's Hub
@pytest.mark.asyncio
async def test_cannot_update_other_owners_hub(client, hub_owner_token, hub_owner2_token):
    """Hub Owner cannot update another Hub Owner's hub."""
    token1, user_id1 = hub_owner_token
    token2, user_id2 = hub_owner2_token
    
    # Owner 1 creates hub
    create_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Protected Hub",
            "address": "Secure Location",
            "city": "Hyderabad",
            "state": "Telangana",
            "country": "India",
            "pincode": "500001"
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    hub_id = create_response.json()["id"]
    
    # Owner 2 tries to update
    response = await client.patch(
        f"/v1/hub-owner/hubs/{hub_id}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    assert response.status_code == 403


# TEST 6: Deactivate Hub
@pytest.mark.asyncio
async def test_deactivate_hub(client, hub_owner_token):
    """Hub Owner can deactivate their hub (soft delete)."""
    token, user_id = hub_owner_token
    
    # Create hub
    create_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "To Delete Hub",
            "address": "Temporary Location",
            "city": "Pune",
            "state": "Maharashtra",
            "country": "India",
            "pincode": "411001"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    hub_id = create_response.json()["id"]
    
    # Deactivate
    deactivate_response = await client.patch(
        f"/v1/hub-owner/hubs/{hub_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert deactivate_response.status_code == 200
    data = deactivate_response.json()
    assert data["is_active"] == False
    
    # Verify hub doesn't appear in list (only active hubs shown)
    list_response = await client.get(
        "/v1/hub-owner/hubs",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_response.json()["total"] == 0


# TEST 7: Admin Can View All Hubs
@pytest.mark.asyncio
async def test_admin_can_view_all_hubs(client, hub_owner_token, hub_owner2_token, admin_token):
    """Admin has read-only access to all hubs."""
    token1, user_id1 = hub_owner_token
    token2, user_id2 = hub_owner2_token
    
    # Create hubs from different owners
    await client.post("/v1/hub-owner/hubs", json={
        "name": "Owner1 Hub", "address": "Addr1", "city": "City1",
        "state": "State1", "country": "India", "pincode": "100001"
    }, headers={"Authorization": f"Bearer {token1}"})
    
    await client.post("/v1/hub-owner/hubs", json={
        "name": "Owner2 Hub", "address": "Addr2", "city": "City2",
        "state": "State2", "country": "India", "pincode": "200001"
    }, headers={"Authorization": f"Bearer {token2}"})
    
    # Admin lists all hubs
    response = await client.get(
        "/v1/admin/hubs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


# TEST 8: Blocked Hub Owner Cannot Create Hub
@pytest.mark.asyncio
async def test_blocked_hub_owner_cannot_create_hub(client, hub_owner_token, admin_token):
    """Blocked Hub Owner cannot create hubs (token revoked)."""
    token, user_id = hub_owner_token
    
    # Admin blocks the hub owner
    await client.post(
        f"/v1/admin/users/{user_id}/block",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={}
    )
    
    # Try to create hub (should fail with 401 or 403)
    response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Blocked Hub",
            "address": "Blocked",
            "city": "Blocked",
            "state": "Blocked",
            "country": "Blocked",
            "pincode": "000000"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should be denied (401 or 403)
    assert response.status_code in [401, 403]


# TEST 9: Audit Logging
@pytest.mark.asyncio
async def test_hub_actions_are_audited(client, hub_owner_token, admin_token):
    """Hub creation and updates are logged in audit trail."""
    token, user_id = hub_owner_token
    
    # Create hub
    create_response = await client.post(
        "/v1/hub-owner/hubs",
        json={
            "name": "Audit Test Hub",
            "address": "Test",
            "city": "Test",
            "state": "Test",
            "country": "Test",
            "pincode": "000000"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    hub_id = create_response.json()["id"]
    
    # Update hub
    await client.patch(
        f"/v1/hub-owner/hubs/{hub_id}",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Deactivate hub
    await client.patch(
        f"/v1/hub-owner/hubs/{hub_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Check audit logs (admin only)
    audit_response = await client.get(
        "/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    
    # Should have HUB_CREATED, HUB_UPDATED, HUB_DEACTIVATED events
    actions = [log["action"] for log in logs]
    assert "HUB_CREATED" in actions
    assert "HUB_UPDATED" in actions
    assert "HUB_DEACTIVATED" in actions
