"""Convergence Engine API — multi-signal M&A target detection."""

from datetime import datetime
from flask import Blueprint, current_app, jsonify

convergence_bp = Blueprint("convergence", __name__)


def _engine():
    return current_app.config["CONVERGENCE_ENGINE"]


def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})


@convergence_bp.get("/signals")
def signals():
    return _ok(_engine().get_signals())


@convergence_bp.get("/heat")
def heat_events():
    return _ok(_engine().get_heat_events())


@convergence_bp.get("/heat/<heat_id>")
def heat_detail(heat_id: str):
    event = _engine().get_heat_event(heat_id)
    if not event:
        return jsonify({"success": False, "error": "not_found"}), 404
    return _ok(event)


@convergence_bp.get("/entity/<entity_name>")
def entity_signals(entity_name: str):
    return _ok(_engine().get_entity_signals(entity_name))


@convergence_bp.get("/patterns")
def patterns():
    return _ok(_engine().get_patterns())


@convergence_bp.get("/stats")
def stats():
    return _ok(_engine().stats())
