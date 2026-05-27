"""Business Development API — EagleEye scanning + pitch generation + outreach."""
from datetime import datetime
from flask import Blueprint, jsonify, request

bd_bp = Blueprint("bd", __name__)

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

def _engine():
    from services.bd_engine import BDEngine
    return BDEngine()

@bd_bp.post("/scan")
def scan():
    body = request.get_json(silent=True) or {}
    sector = body.get("sector", "senior_living")
    return _ok(_engine().scan_sector(sector, body.get("keywords")))

@bd_bp.post("/pitch")
def pitch():
    body = request.get_json(silent=True) or {}
    return _ok(_engine().generate_pitch(body.get("target", {}), body.get("sector", "senior_living")))

@bd_bp.post("/email")
def email():
    body = request.get_json(silent=True) or {}
    target = body.get("target", {})
    pitch = body.get("pitch", {})
    return _ok(_engine().generate_outreach_email(target, pitch))

@bd_bp.post("/campaign")
def campaign():
    body = request.get_json(silent=True) or {}
    return _ok(_engine().generate_campaign(body.get("targets", []), body.get("sector", "senior_living")))

@bd_bp.post("/qualify")
def qualify():
    body = request.get_json(silent=True) or {}
    return _ok(_engine().qualify_target(body.get("target", {}), body.get("sector", "senior_living")))

@bd_bp.post("/silo-check")
def silo_check():
    body = request.get_json(silent=True) or {}
    return _ok(_engine().silo_check(body.get("deals", [])))
