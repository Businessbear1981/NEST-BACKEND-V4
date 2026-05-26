from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

phoenix_bp = Blueprint("phoenix", __name__)


def _engine():
    return current_app.config["PHOENIX_ENGINE"]


def _ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ── Deal pipeline ─────────────────────────────────────────────────────

@phoenix_bp.get("/deals")
def list_deals():
    return _ok(_engine().list_deals())


@phoenix_bp.get("/deals/<deal_id>")
def get_deal(deal_id: str):
    deal = _engine().get_deal(deal_id)
    if not deal:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(deal)


@phoenix_bp.post("/deals")
def create_deal():
    body = request.get_json(silent=True) or {}
    return _ok(_engine().create_deal(body)), 201


@phoenix_bp.put("/deals/<deal_id>")
def update_deal(deal_id: str):
    body = request.get_json(silent=True) or {}
    deal = _engine().update_deal(deal_id, body)
    if not deal:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(deal)


# ── Underwriting ──────────────────────────────────────────────────────

@phoenix_bp.get("/deals/<deal_id>/underwriting")
def get_underwriting(deal_id: str):
    uw = _engine().underwriting(deal_id)
    if not uw:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(uw)


@phoenix_bp.post("/deals/<deal_id>/underwriting")
def run_underwriting(deal_id: str):
    uw = _engine().underwriting(deal_id)
    if not uw:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(uw), 201


# ── Timeline ──────────────────────────────────────────────────────────

@phoenix_bp.get("/deals/<deal_id>/timeline")
def get_timeline(deal_id: str):
    tl = _engine().timeline(deal_id)
    if not tl:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(tl)


@phoenix_bp.put("/deals/<deal_id>/timeline/<milestone_id>")
def update_milestone(deal_id: str, milestone_id: str):
    body = request.get_json(silent=True) or {}
    tl = _engine().timeline(deal_id)
    if not tl:
        return jsonify({"success": False, "error": "not_found"}), 404
    for ms in tl["milestones"]:
        if ms["id"] == milestone_id:
            ms["status"] = body.get("status", ms["status"])
    return _ok(tl)


# ── Bond handoff ──────────────────────────────────────────────────────

@phoenix_bp.get("/deals/<deal_id>/bond-handoff")
def get_bond_handoff(deal_id: str):
    ho = _engine().bond_handoff(deal_id)
    if not ho:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(ho)


@phoenix_bp.post("/deals/<deal_id>/bond-handoff")
def push_bond_handoff(deal_id: str):
    ho = _engine().bond_handoff(deal_id)
    if not ho:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok({**ho, "pushed": True, "message": "Deal pushed to Bond Desk."}), 201


# ── Sourcing radar ────────────────────────────────────────────────────

@phoenix_bp.get("/radar/feed")
def radar_feed():
    return _ok(_engine().radar_feed())


@phoenix_bp.get("/radar/scores")
def radar_scores():
    return _ok(_engine().radar_scores())


# ── Warchest ──────────────────────────────────────────────────────────

@phoenix_bp.get("/warchest")
def warchest():
    return _ok(_engine().warchest())


@phoenix_bp.get("/warchest/economics")
def warchest_economics():
    return _ok(_engine().warchest_economics())
