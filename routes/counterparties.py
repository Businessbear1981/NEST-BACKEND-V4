"""Counterparty Database API — Appendix E of Operating Framework."""
from datetime import datetime
from flask import Blueprint, jsonify, request

counterparties_bp = Blueprint("counterparties", __name__)

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

@counterparties_bp.get("/")
def all_counterparties():
    from services.counterparty_db import get_all_counterparties
    return _ok(get_all_counterparties())

@counterparties_bp.get("/<role>")
def by_role(role: str):
    from services.counterparty_db import get_counterparties_by_role
    result = get_counterparties_by_role(role)
    return _ok({"role": role, "counterparties": result, "count": len(result)})

@counterparties_bp.get("/feasibility/<sector>")
def feasibility(sector: str):
    from services.counterparty_db import get_feasibility_consultants
    result = get_feasibility_consultants(sector)
    return _ok({"sector": sector, "consultants": result, "count": len(result)})
