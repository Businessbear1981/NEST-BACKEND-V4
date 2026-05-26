"""
Desk management and Bernard CEO API.
Exposes the Operating Framework's organizational structure and Bernard orchestrator.
"""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

desks_bp = Blueprint("desks", __name__)


def _ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ── Desk Registry Endpoints ──────────────────────────────────

@desks_bp.get("/")
def list_desks():
    from agents.desk_registry import DESKS, ORCA_CSUITE, get_desk_summary
    return _ok({
        "orca": ORCA_CSUITE,
        "desks": DESKS,
        "summary": get_desk_summary(),
    })


@desks_bp.get("/<desk_id>")
def get_desk(desk_id: str):
    from agents.desk_registry import DESKS
    desk = DESKS.get(desk_id)
    if not desk:
        return jsonify({"success": False, "error": f"Desk '{desk_id}' not found", "timestamp": datetime.utcnow().isoformat()}), 404
    return _ok(desk)


@desks_bp.get("/<desk_id>/agents")
def desk_agents(desk_id: str):
    from agents.desk_registry import get_desk_agents
    agents = get_desk_agents(desk_id)
    return _ok(agents)


@desks_bp.get("/agents/all")
def all_agents():
    from agents.desk_registry import get_all_agents
    return _ok(get_all_agents())


@desks_bp.get("/agents/lookup/<agent_name>")
def lookup_agent(agent_name: str):
    from agents.desk_registry import get_desk_for_agent
    result = get_desk_for_agent(agent_name)
    if not result:
        return jsonify({"success": False, "error": f"Agent '{agent_name}' not found", "timestamp": datetime.utcnow().isoformat()}), 404
    return _ok(result)


# ── Bernard CEO Endpoints ────────────────────────────────────

def _get_bernard():
    bernard = current_app.config.get("BERNARD")
    if not bernard:
        from agents.bernard import BernardAgent
        bernard = BernardAgent()
        current_app.config["BERNARD"] = bernard
    return bernard


@desks_bp.post("/bernard/ask")
def bernard_ask():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "")
    context = body.get("context")
    if not question:
        return jsonify({"success": False, "error": "question required", "timestamp": datetime.utcnow().isoformat()}), 400
    result = _get_bernard().ask(question, context)
    return _ok(result)


@desks_bp.post("/bernard/route")
def bernard_route():
    body = request.get_json(silent=True) or {}
    task = body.get("task", "")
    if not task:
        return jsonify({"success": False, "error": "task required", "timestamp": datetime.utcnow().isoformat()}), 400
    result = _get_bernard().route(task)
    return _ok(result)


@desks_bp.post("/bernard/tutorial")
def bernard_tutorial():
    body = request.get_json(silent=True) or {}
    decision_point = body.get("decision_point", "")
    context = body.get("context")
    if not decision_point:
        return jsonify({"success": False, "error": "decision_point required", "timestamp": datetime.utcnow().isoformat()}), 400
    result = _get_bernard().tutorial(decision_point, context)
    return _ok(result)


@desks_bp.post("/bernard/narrate")
def bernard_narrate():
    body = request.get_json(silent=True) or {}
    event = body.get("event", "")
    deal_context = body.get("deal_context")
    if not event:
        return jsonify({"success": False, "error": "event required", "timestamp": datetime.utcnow().isoformat()}), 400
    result = _get_bernard().narrate(event, deal_context)
    return _ok({"narration": result})


@desks_bp.post("/bernard/firm-review")
def bernard_firm_review():
    body = request.get_json(silent=True) or {}
    result = _get_bernard().firm_review(
        deals=body.get("deals"),
        metrics=body.get("metrics"),
    )
    return _ok({"review": result})
