"""
NEST Power Strip Routes — Exposes the universal PluginHub to the frontend.
Tier 3: Backend → Frontend
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth
from datetime import datetime
from services.auth import require_auth

powerstrip_bp = Blueprint("powerstrip", __name__)


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


# ── STATUS: What plugins are configured & healthy? ───────────────

@powerstrip_bp.route("/status", methods=["GET"])
def status():
    from services.ai_router import plugin_hub
    return _ok(plugin_hub.get_tool_status())


@powerstrip_bp.route("/plugins", methods=["GET"])
def list_plugins():
    from services.ai_router import plugin_hub
    return _ok(plugin_hub.list_plugins())


# ── ROUTE: Send a task to the best plugin ────────────────────────

@powerstrip_bp.route("/route", methods=["POST"])
def route_task():
    b = request.get_json() or {}
    task_type = b.get("task_type")
    prompt = b.get("prompt")
    if not task_type or not prompt:
        return _err("task_type and prompt are required")

    from services.ai_router import plugin_hub
    result = plugin_hub.route(
        task_type=task_type,
        prompt=prompt,
        system=b.get("system"),
        force_tool=b.get("force_tool"),
    )
    return _ok(result)


# ── DIRECT: Call a specific plugin by name ───────────────────────

@powerstrip_bp.route("/call/<plugin_name>", methods=["POST"])
def call_plugin(plugin_name):
    b = request.get_json() or {}
    prompt = b.get("prompt")
    if not prompt:
        return _err("prompt is required")

    from services.ai_router import plugin_hub
    result = plugin_hub.call_direct(plugin_name, prompt, b.get("system"))
    return _ok(result)


# ── MARKET RATES: Live treasury, SOFR, spreads ───────────────────

@powerstrip_bp.route("/market-rates", methods=["GET"])
def market_rates():
    from services.ai_router import plugin_hub
    return _ok(plugin_hub.get_market_rates())


# ── BOND PRICING: Bloomberg → internal engine fallback ───────────

@powerstrip_bp.route("/bond-pricing", methods=["POST"])
def bond_pricing():
    b = request.get_json() or {}
    from services.ai_router import plugin_hub
    return _ok(plugin_hub.get_bond_pricing(b))


# ── REFI SIGNALS: Call/put opportunity detection ─────────────────

@powerstrip_bp.route("/refi-signals", methods=["POST"])
def refi_signals():
    b = request.get_json() or {}
    if not b.get("bond_face_usd"):
        return _err("bond_face_usd is required")

    from services.ai_router import plugin_hub
    return _ok(plugin_hub.get_refi_signals(b))
