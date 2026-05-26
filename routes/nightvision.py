"""
NEST NightVision Routes — Compliance Intelligence Layer.
Real rule-based compliance scanning for institutional bond deals.
from services.auth import require_auth
SEC, FINRA/MSRB, BSA/AML, State Licensing, Tax/IRS.
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth, current_user
from datetime import datetime

nightvision_bp = Blueprint("nightvision", __name__)

try:
    from services.core import ok, err
except ImportError:
    def ok(d, c=200):
        return jsonify({"success": True, "data": d, "error": None,
                        "timestamp": datetime.utcnow().isoformat()}), c

    def err(m, c=400):
        return jsonify({"success": False, "data": None, "error": m,
                        "timestamp": datetime.utcnow().isoformat()}), c

from services.compliance_engine import compliance_engine, run_compliance_scan, get_check_definitions


# ── COMPLIANCE SCAN ──────────────────────────────────────────────

@nightvision_bp.route("/scan", methods=["POST"])
@require_auth()
def compliance_scan():
    """
    Run a full compliance scan against deal data.

    POST body:
    {
        "deal_type": "REVENUE_BOND",
        "offering_type": "506C",
        "amount_usd": 231000000,
        "issuer_state": "FL",
        "target_states": ["FL", "TX", "AZ"],
        "project_type": "senior_living",
        "tax_exempt": true,
        "participants": {"underwriter": {"finra_registered": true, "crd_number": "12345"}},
        "investors": [{"name": "Investor A", "kyc_verified": true}],
        ...
    }
    """
    body = request.get_json() or {}
    if not body:
        return err("Deal data required. Provide at minimum: deal_type, amount_usd, issuer_state.")

    result = run_compliance_scan(body)
    return ok(result)


@nightvision_bp.route("/scan/<deal_id>", methods=["POST"])
@require_auth()
def compliance_scan_by_deal(deal_id):
    """
    Run compliance scan for an existing deal by ID.
    Merges stored deal data with any overrides in POST body.
    """
    body = request.get_json() or {}

    # Try to pull deal from deals registry
    from flask import current_app
    deals = current_app.config.get("DEALS")
    deal_data = {}
    if deals and hasattr(deals, "get"):
        stored = deals.get(deal_id)
        if stored:
            deal_data = {
                "deal_type": stored.get("bond_type", stored.get("deal_type", "")),
                "amount_usd": stored.get("project", {}).get("total_project_cost_usd",
                              stored.get("amount_usd", 0)),
                "issuer_state": stored.get("project", {}).get("state",
                                stored.get("issuer_state", "")),
                "project_type": stored.get("project", {}).get("type",
                                stored.get("project_type", "")),
            }

    # Merge: body overrides stored data
    deal_data.update(body)
    deal_data["deal_id"] = deal_id

    if not deal_data.get("deal_type") and not deal_data.get("amount_usd"):
        return err(f"Deal '{deal_id}' not found and no deal data provided in request body.", 404)

    result = run_compliance_scan(deal_data)
    return ok(result)


# ── CHECK DEFINITIONS ────────────────────────────────────────────

@nightvision_bp.route("/checks", methods=["GET"])
def check_definitions():
    """Return the full compliance check catalog — all categories, all checks."""
    return ok(get_check_definitions())


@nightvision_bp.route("/checks/<category>", methods=["GET"])
def check_definitions_by_category(category):
    """Return compliance checks for a specific category (sec, finra, bsa_aml, state, tax)."""
    defs = get_check_definitions()
    cat = defs.get(category.lower())
    if not cat:
        valid = ", ".join(defs.keys())
        return err(f"Category '{category}' not found. Valid: {valid}.", 404)
    return ok(cat)


# ── QUICK STATUS ─────────────────────────────────────────────────

@nightvision_bp.route("/status", methods=["GET"])
@require_auth()
def nightvision_status():
    """Quick status endpoint — returns engine version and category summary."""
    return ok({
        "engine": "NightVision Compliance Engine v1.0",
        "categories": ["sec", "finra", "bsa_aml", "state", "tax"],
        "total_check_types": sum(
            len(cat["checks"]) for cat in get_check_definitions().values()
        ),
        "state_coverage": list(
            __import__("services.compliance_engine", fromlist=["STATE_REQUIREMENTS"]).STATE_REQUIREMENTS.keys()
        ),
        "operational": True,
    })


# ── DEAL GATE CHECK ─────────────────────────────────────────────

@nightvision_bp.route("/gate-check", methods=["POST"])
@require_auth()
def gate_check():
    """
    Quick gate check — returns only blockers and whether the deal can proceed.
    Lighter than a full scan for pipeline UI integration.
    """
    body = request.get_json() or {}
    if not body:
        return err("Deal data required.")

    result = run_compliance_scan(body)
    return ok({
        "can_proceed": result["overall"]["can_proceed"],
        "gate_status": result["overall"]["gate_status"],
        "gate_message": result["overall"]["gate_message"],
        "score": result["overall"]["score"],
        "blocker_count": len(result["blockers"]),
        "blockers": result["blockers"],
        "warning_count": result["overall"]["warn"],
    })
