"""
Cross-Desk Workflow API — Deal lifecycle orchestration.
BD → Bond Desk → Credit → Rating → Structuring → Documents → Placement → Operations → Surveillance
"""
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request

workflow_bp = Blueprint("workflow", __name__)

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

def _engine():
    engine = current_app.config.get("WORKFLOW_ENGINE")
    if not engine:
        from services.workflow_engine import WorkflowEngine
        engine = WorkflowEngine()
        current_app.config["WORKFLOW_ENGINE"] = engine
    return engine

@workflow_bp.get("/stages")
def stages():
    return _ok(_engine().get_stages())

@workflow_bp.get("/pipeline")
def pipeline():
    return _ok(_engine().get_pipeline())

@workflow_bp.post("/init")
def init_deal():
    body = request.get_json(silent=True) or {}
    deal_id = body.get("deal_id", "")
    deal_type = body.get("deal_type", "ma_acquisition")
    source = body.get("source", "inbound")
    if not deal_id:
        return jsonify({"success": False, "error": "deal_id required"}), 400
    result = _engine().init_deal(deal_id, deal_type, source)
    return _ok(result), 201

@workflow_bp.get("/<deal_id>")
def get_workflow(deal_id: str):
    result = _engine().get_deal_workflow(deal_id)
    if not result:
        return jsonify({"success": False, "error": "Deal not found"}), 404
    return _ok(result)

@workflow_bp.post("/<deal_id>/gate")
def pass_gate(deal_id: str):
    body = request.get_json(silent=True) or {}
    gate = body.get("gate_condition", "")
    if not gate:
        return jsonify({"success": False, "error": "gate_condition required"}), 400
    result = _engine().pass_gate(deal_id, gate)
    return _ok(result)

@workflow_bp.post("/<deal_id>/advance")
def advance(deal_id: str):
    result = _engine().advance_stage(deal_id)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"], "data": result}), 400
    return _ok(result)

@workflow_bp.get("/<deal_id>/stage")
def current_stage(deal_id: str):
    result = _engine().get_current_stage(deal_id)
    if not result:
        return jsonify({"success": False, "error": "Deal not found or invalid stage"}), 404
    return _ok(result)
