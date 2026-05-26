"""Shared fixtures for NEST backend tests."""
import os
import sys
import pytest

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Prevent SocketIO ticker thread from spawning during tests
os.environ["VERCEL"] = "1"


@pytest.fixture()
def app():
    """Create a Flask app in testing mode."""
    from app import create_app

    flask_app, _ = create_app()
    flask_app.config.update({"TESTING": True})
    yield flask_app


@pytest.fixture()
def client(app):
    """Flask test client — use for HTTP assertions."""
    return app.test_client()


@pytest.fixture()
def auth_header(client):
    """Return an Authorization header dict for the seeded admin user."""
    resp = client.post("/api/auth/login", json={
        "email": "admin@nest.local",
        "password": "Admin123!",
    })
    token = resp.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
