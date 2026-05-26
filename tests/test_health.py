"""Tests for /api/health endpoints."""


def test_liveness_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["service"] == "nest-backend"
    assert "uptime_seconds" in data
    assert "timestamp" in data


def test_readiness_returns_structured_checks(client):
    resp = client.get("/api/health/ready")
    # May return 200 or 503 depending on env vars — both are valid in test
    data = resp.get_json()
    assert "ok" in data
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "checks" in data
    # Should always include at least anthropic + fred + supabase keys
    assert "anthropic" in data["checks"]
    assert "fred" in data["checks"]
    assert "supabase" in data["checks"]
