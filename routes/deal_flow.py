"""Deal Flow API — runs deals through the desk pipeline."""
from datetime import datetime
from flask import Blueprint, jsonify, request

deal_flow_bp = Blueprint("deal_flow", __name__)

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

@deal_flow_bp.post("/run")
def run_pipeline():
    """Run a deal through the full pipeline (intake → credit → rating → structuring)."""
    body = request.get_json(silent=True) or {}
    from services.deal_flow import DealFlow
    return _ok(DealFlow().run_full_pipeline(body))

@deal_flow_bp.post("/intake")
def run_intake():
    body = request.get_json(silent=True) or {}
    from services.deal_flow import DealFlow
    return _ok(DealFlow().run_intake(body))

@deal_flow_bp.post("/credit")
def run_credit():
    body = request.get_json(silent=True) or {}
    from services.deal_flow import DealFlow
    return _ok(DealFlow().run_credit(body))

@deal_flow_bp.post("/rating")
def run_rating():
    body = request.get_json(silent=True) or {}
    from services.deal_flow import DealFlow
    return _ok(DealFlow().run_rating(body))

@deal_flow_bp.post("/structuring")
def run_structuring():
    body = request.get_json(silent=True) or {}
    from services.deal_flow import DealFlow
    return _ok(DealFlow().run_structuring(body))

@deal_flow_bp.get("/seed-deals")
def seed_deals():
    """Get the EMMA seed deals for pipeline display."""
    from services.emma_seed_data import get_seed_deals_for_pipeline
    return _ok(get_seed_deals_for_pipeline())
