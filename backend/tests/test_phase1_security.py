"""
Integration tests for Phase 1 Security Features.

Tests token revocation, admin APIs, and ownership guards.
"""

import pytest
from backend.app.models.enums import UserRole

# Note: Client and DB setup are now in conftest.py


@pytest.fixture
async def admin_token(client, db_session):
    """Create admin user and return auth token."""
    # Register admin manually (via seed or direct DB insert)
    # For testing, we'll create via registration endpoint and manually set superuser
    
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

@pytest.fixture
async def fleet_owner_token(client):
    """Create fleet owner and return auth token."""
    response = await client.post("/v1/auth/register", json={
        "email": "owner@test.com",
        "username": "fleetowner",
        "password": "password123",
        "role": "FLEET_OWNER"
    })
    assert response.status_code == 201
    return response.json()["access_token"]


# TEST 1: Token Revocation
@pytest.mark.asyncio
async def test_blocked_user_loses_access_immediately(client, admin_token, fleet_owner_token):
    """
    CRITICAL: Blocked user should receive 401 immediately, not after token expiry.
    """
    # 1. Create a test user
    register_response = await client.post("/v1/auth/register", json={
        "email": "testuser@test.com",
        "username": "testuser",
        "password": "password123",
        "role": "FLEET_OWNER"
    })
    assert register_response.status_code == 201
    user_token = register_response.json()["access_token"]
    user_id = register_response.json()["user_id"]
    
    # 2. Verify user can access protected endpoint
    me_response = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_response.status_code == 200
    
    # 3. Admin blocks the user
    block_response = await client.post(
        f"/v1/admin/users/{user_id}/block",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Test block"}
    )
    assert block_response.status_code == 200
    
    # 4. CRITICAL TEST: User should be denied immediately
    me_response_after_block = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_response_after_block.status_code == 401
    assert "revoked" in me_response_after_block.json()["message"].lower() or "inactive" in me_response_after_block.json()["message"].lower()


# TEST 2: Admin Can List Users
@pytest.mark.asyncio
async def test_admin_can_list_users(client, admin_token, fleet_owner_token):
    """
    Admin should be able to list all users in the system.
    """
    response = await client.get("/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert data["total"] >= 2  # At least admin and fleet owner


# TEST 3: Non-Admin Cannot Access Admin Endpoints
@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(client, fleet_owner_token):
    """
    Non-admin users should receive 403 when accessing admin endpoints.
    """
    response = await client.get("/v1/admin/users", headers={"Authorization": f"Bearer {fleet_owner_token}"})
    assert response.status_code == 403


# TEST 4: Audit Logging
@pytest.mark.asyncio
async def test_block_action_is_audited(client, admin_token):
    """
    Blocking a user should create an audit log entry.
    """
    # Create user
    register_response = await client.post("/v1/auth/register", json={
        "email": "audituser@test.com",
        "username": "audituser",
        "password": "password123",
        "role": "FLEET_OWNER"
    })
    user_id = register_response.json()["user_id"]
    
    # Block user
    block_response = await client.post(
        f"/v1/admin/users/{user_id}/block",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Test audit"}
    )
    audit_log_id = block_response.json()["audit_log_id"]
    
    # Verify audit log exists
    audit_response = await client.get(
        f"/v1/admin/users/{user_id}/audit-history",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    assert len(logs) > 0
    assert any(log["action"] == "USER_BLOCKED" for log in logs)


# TEST 5: Login Audit Logging
@pytest.mark.asyncio
async def test_failed_login_is_audited(client, admin_token):
    """
    Failed login attempts should be logged in audit trail.
    """
    # Attempt login with wrong password
    login_response = await client.post("/v1/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert login_response.status_code == 401
    
    # Check audit logs
    audit_response = await client.get(
        "/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert audit_response.status_code == 200
    logs = audit_response.json()["logs"]
    
    # Should have LOGIN_FAILED event
    assert any(log["action"] == "LOGIN_FAILED" for log in logs)


# TEST 6: Unblock User
@pytest.mark.asyncio
async def test_unblock_user_allows_login(client, admin_token):
    """
    Unblocked user should be able to login again.
    """
    # Create and block user
    register_response = await client.post("/v1/auth/register", json={
        "email": "unblocktest@test.com",
        "username": "unblocktest",
        "password": "password123",
        "role": "FLEET_OWNER"
    })
    user_id = register_response.json()["user_id"]
    
    await client.post(
        f"/v1/admin/users/{user_id}/block",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={}
    )
    
    # Try to login (should fail)
    login_response = await client.post("/v1/auth/login", json={
        "username": "unblocktest",
        "password": "password123"
    })
    assert login_response.status_code == 403  # Inactive account
    
    # Unblock user
    unblock_response = await client.post(
        f"/v1/admin/users/{user_id}/unblock",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={}
    )
    assert unblock_response.status_code == 200
    
    # Try to login again (should succeed)
    login_response2 = await client.post("/v1/auth/login", json={
        "username": "unblocktest",
        "password": "password123"
    })
    assert login_response2.status_code == 200


# TEST 7: Error Response Consistency
@pytest.mark.asyncio
async def test_error_responses_are_consistent(client):
    """
    All error responses should follow consistent format with error_code.
    """
    # Test 404
    response = await client.get("/v1/auth/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "error_code" in data
    assert "message" in data
    
    # Test 401
    response = await client.get("/v1/auth/me")  # No token
    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


# TEST 8: Role Guard
@pytest.mark.asyncio
async def test_role_guards_work(client, admin_token, fleet_owner_token):
    """
    Role guards should enforce role-based access.
    """
    # Admin can access admin endpoints
    response = await client.get("/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    
    # Fleet Owner cannot
    response = await client.get("/v1/admin/users", headers={"Authorization": f"Bearer {fleet_owner_token}"})
    assert response.status_code == 403
