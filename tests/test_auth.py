"""Tests for /api/auth endpoints — registration, login, token gating."""
import pytest


def test_register_new_client(client):
    import uuid
    unique_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "TestPass123!",
        "name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert "token" in data
    assert data["user"]["email"] == unique_email
    assert data["user"]["role"] == "client"


def test_register_duplicate_email(client):
    """Seeded admin email should conflict."""
    resp = client.post("/api/auth/register", json={
        "email": "admin@nest.local",
        "password": "AnotherPass1!",
        "name": "Dup Admin",
    })
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_register_short_password(client):
    resp = client.post("/api/auth/register", json={
        "email": "short@example.com",
        "password": "abc",
        "name": "Short PW",
    })
    assert resp.status_code == 400


def test_login_valid_credentials(client):
    resp = client.post("/api/auth/login", json={
        "email": "admin@nest.local",
        "password": "Admin123!",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
    assert data["user"]["role"] == "admin"


def test_login_invalid_password(client):
    resp = client.post("/api/auth/login", json={
        "email": "admin@nest.local",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "Whatever1!",
    })
    assert resp.status_code == 401


def test_protected_route_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_protected_route_with_valid_token(client, auth_header):
    resp = client.get("/api/auth/me", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email"] == "admin@nest.local"
    assert data["role"] == "admin"


def test_protected_route_with_bogus_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert resp.status_code == 401
