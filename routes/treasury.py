from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

treasury_bp = Blueprint("treasury", __name__)


def _engine():
    return current_app.config["TREASURY_ENGINE"]


def _ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ── Deal-scoped endpoints ────────────────────────────────────────────

@treasury_bp.get("/<deal_id>/overview")
def overview(deal_id: str):
    return _ok(_engine().overview(deal_id))


@treasury_bp.get("/<deal_id>/transactions")
def transactions(deal_id: str):
    return _ok(_engine().transactions(deal_id))


@treasury_bp.get("/<deal_id>/cards")
def cards(deal_id: str):
    return _ok(_engine().cards(deal_id))


@treasury_bp.get("/<deal_id>/budget")
def budget(deal_id: str):
    return _ok(_engine().budget(deal_id))


@treasury_bp.get("/<deal_id>/draws")
def draws(deal_id: str):
    return _ok(_engine().prefund_history(deal_id))


@treasury_bp.get("/<deal_id>/reconciliation")
def reconciliation(deal_id: str):
    return _ok(_engine().reconciliation(deal_id))


@treasury_bp.get("/<deal_id>/rebate")
def rebate(deal_id: str):
    return _ok(_engine().rebate(deal_id))


@treasury_bp.post("/<deal_id>/prefund")
def prefund(deal_id: str):
    body = request.get_json(silent=True) or {}
    amount = body.get("amount", 0)
    return _ok({
        "status": "submitted",
        "deal_id": deal_id,
        "amount": amount,
        "message": "Prefund request submitted to approval rail.",
        "requires_approval": True,
    }), 201


@treasury_bp.post("/<deal_id>/cards")
def issue_card(deal_id: str):
    body = request.get_json(silent=True) or {}
    return _ok({
        "status": "issued",
        "deal_id": deal_id,
        "vendor": body.get("vendor", "Unknown"),
        "category": body.get("category", "General"),
        "limit": body.get("limit", 0),
        "message": "Virtual card issued.",
    }), 201


# ── NEST-scoped endpoints ────────────────────────────────────────────

@treasury_bp.get("/nest/soft-costs")
def nest_soft_costs():
    return _ok(_engine().nest_soft_costs())


@treasury_bp.get("/nest/reimbursement/<deal_id>")
def nest_reimbursement(deal_id: str):
    return _ok(_engine().nest_reimbursement(deal_id))


@treasury_bp.get("/portfolio")
def portfolio():
    return _ok(_engine().portfolio())
