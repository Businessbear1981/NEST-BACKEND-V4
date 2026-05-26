"""Tests for /api/deals endpoints — CRUD, backed by Supabase or in-memory fallback."""


def test_create_deal(client, auth_header):
    resp = client.post("/api/deals", json={
        "name": "Test Tower Deal",
        "project": {
            "name": "Test Tower",
            "city": "Seattle",
            "state": "WA",
            "asset_type": "mixed_use",
            "total_project_cost_usd": 50_000_000,
        },
        "sponsor": {"entity_name": "Test Sponsor LLC"},
    }, headers=auth_header)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    deal = data["data"]
    assert deal["name"] == "Test Tower Deal"
    assert "id" in deal
    # Status is "intake" in-memory or "pipeline" when mapped to Supabase
    assert deal["status"] in ("intake", "pipeline")


def test_create_deal_missing_name(client, auth_header):
    resp = client.post("/api/deals", json={"project": {}}, headers=auth_header)
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_list_deals(client, auth_header):
    resp = client.get("/api/deals", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    # Seed data creates 3 deals; prior tests may have added more
    assert len(data["data"]) >= 3


def test_list_deals_filter_by_status(client, auth_header):
    resp = client.get("/api/deals?status=active", headers=auth_header)
    assert resp.status_code == 200
    deals = resp.get_json()["data"]
    for d in deals:
        assert d["status"] == "active"


def test_get_single_deal(client, auth_header):
    create_resp = client.post("/api/deals", json={
        "name": "Lookup Test",
        "project": {"city": "Portland"},
    }, headers=auth_header)
    deal_id = create_resp.get_json()["data"]["id"]

    resp = client.get(f"/api/deals/{deal_id}", headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == deal_id


def test_get_deal_not_found(client, auth_header):
    resp = client.get("/api/deals/nonexistent-id-999", headers=auth_header)
    assert resp.status_code == 404
    assert resp.get_json()["success"] is False


def test_update_deal(client, auth_header):
    create_resp = client.post("/api/deals", json={"name": "Patch Test"}, headers=auth_header)
    deal_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/api/deals/{deal_id}", json={"status": "active"}, headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "active"


def test_deals_require_auth(client):
    """Verify that deal endpoints return 401 without auth."""
    resp = client.get("/api/deals")
    assert resp.status_code == 401
