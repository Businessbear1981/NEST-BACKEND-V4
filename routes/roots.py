"""NEST Roots Marketplace Routes"""
from flask import Blueprint, request

roots_bp = Blueprint("roots", __name__)

from services.core import ok, err
from services.auth import require_auth
from services.roots_service import roots_service


@roots_bp.route("/api/roots/offerings", methods=["GET"])
def get_offerings():
    """Public — no auth. Anyone can browse offerings."""
    filters = {}
    if request.args.get("asset_type"):
        filters["asset_type"] = request.args["asset_type"]
    if request.args.get("state"):
        filters["state"] = request.args["state"]
    if request.args.get("bond_ready"):
        filters["bond_ready"] = True
    if request.args.get("max_min_investment"):
        filters["max_min_investment"] = request.args["max_min_investment"]
    return ok(roots_service.get_offerings(filters))


@roots_bp.route("/api/roots/offerings/<offering_id>", methods=["GET"])
def get_offering(offering_id):
    """Public — single offering detail."""
    o = roots_service.get_offering(offering_id)
    if not o:
        return err("Offering not found", 404)
    return ok(o)


@roots_bp.route("/api/roots/offerings/<offering_id>/readiness", methods=["GET"])
def bond_readiness(offering_id):
    """Public — bond readiness checklist."""
    return ok(roots_service.get_bond_readiness(offering_id))


@roots_bp.route("/api/roots/interest", methods=["POST"])
def register_interest():
    """
    Investor registers interest in an offering.
    Public endpoint — no login required.
    Must certify accredited status.
    """
    body = request.get_json() or {}

    if not body.get("offering_id"):
        return err("offering_id required")
    if not body.get("email"):
        return err("Email required")
    if not body.get("name"):
        return err("Name required")
    if not body.get("accredited"):
        return err("Accredited investor certification required to proceed")

    result = roots_service.register_interest(
        body["offering_id"],
        {
            "name": body.get("name"),
            "email": body.get("email"),
            "type": body.get("investor_type", "accredited"),
            "amount": body.get("investment_amount_usd", 0),
            "accredited": body.get("accredited", False),
            "notes": body.get("notes", ""),
        }
    )
    if not result.get("success"):
        return err(result.get("error", "Error processing request"))
    return ok(result)


@roots_bp.route("/api/roots/submit-deal", methods=["POST"])
def submit_deal():
    """
    Broker or client submits a deal to NEST.
    Public endpoint — no login required.
    """
    body = request.get_json() or {}

    required = ["contact_name", "contact_email", "project_name",
                "asset_type", "city", "state", "loan_amount_usd"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return err(f"Missing required fields: {', '.join(missing)}")

    result = roots_service.submit_deal(body)
    return ok(result)


@roots_bp.route("/api/roots/submissions", methods=["GET"])
@require_auth("admin")
def get_submissions():
    """Admin only — view all deal submissions."""
    return ok(roots_service.get_all_submissions())


@roots_bp.route("/api/roots/interests", methods=["GET"])
@require_auth("admin")
def get_interests():
    """Admin only — view all investor interest records."""
    return ok(roots_service.get_all_interests())


@roots_bp.route("/api/roots/submissions/<sub_id>/status", methods=["PATCH"])
@require_auth("admin")
def update_submission(sub_id):
    """Admin — update deal submission review status."""
    body = request.get_json() or {}
    result = roots_service.update_submission_status(
        sub_id,
        body.get("status", "reviewing"),
        body.get("notes", "")
    )
    return ok(result)
