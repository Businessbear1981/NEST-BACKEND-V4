"""
Intelligence Engine API — Bond sizing, underwriting, structuring, pricing.
Exposes the core bond math from Operating Framework + Use Case Manual.
"""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

intel_engine_bp = Blueprint("intel_engine", __name__)


def _ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    })


def _engine():
    engine = current_app.config.get("INTEL_ENGINE")
    if not engine:
        from services.intelligence_engine import IntelligenceEngine
        engine = IntelligenceEngine()
        current_app.config["INTEL_ENGINE"] = engine
    return engine


@intel_engine_bp.post("/size")
def size_bond():
    """Size a bond for any deal type.

    Body: { deal_type, ebitda, sector, acquisition_multiple, ... }
    Returns full sizing with sources/uses, credit grade, pricing, readiness flags.
    """
    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"success": False, "error": "JSON body required", "timestamp": datetime.utcnow().isoformat()}), 400
    result = _engine().size_bond(body)
    return _ok(result)


@intel_engine_bp.post("/size/ma")
def size_ma():
    """Size an M&A acquisition bond (Use Case Manual Ch.1)."""
    body = request.get_json(silent=True) or {}
    result = _engine().size_ma_acquisition(body)
    return _ok(result)


@intel_engine_bp.post("/underwrite")
def underwrite():
    """Run Universal Credit Policy against a deal.

    Body: { dscr, total_leverage, equity_pct, sponsor_experience_years, deal_type }
    """
    body = request.get_json(silent=True) or {}
    result = _engine().underwrite(body)
    return _ok(result)


@intel_engine_bp.post("/covenants")
def build_covenants():
    """Build a covenant package for a deal.

    Body: { deal_type, credit_grade, sector }
    """
    body = request.get_json(silent=True) or {}
    deal_type = body.get("deal_type", "ma_acquisition")
    credit_grade = body.get("credit_grade", "BBB")
    sector = body.get("sector", "business_services")
    result = _engine().build_covenant_package(deal_type, credit_grade, sector)
    return _ok(result)


@intel_engine_bp.get("/sectors")
def list_sectors():
    """List all sectors with multiple ranges and leverage capacity."""
    from services.intelligence_engine import SECTOR_MULTIPLES, SECTOR_LEVERAGE_CAPACITY
    sectors = {}
    for key in SECTOR_MULTIPLES:
        sectors[key] = {
            **SECTOR_MULTIPLES[key],
            **SECTOR_LEVERAGE_CAPACITY.get(key, {}),
        }
    return _ok(sectors)


@intel_engine_bp.get("/credit-policy")
def credit_policy():
    """Return the Universal Credit Policy (Appendix F)."""
    from services.intelligence_engine import UNIVERSAL_CREDIT_POLICY
    return _ok(UNIVERSAL_CREDIT_POLICY)


@intel_engine_bp.get("/pricing")
def pricing_benchmarks():
    """Return pricing benchmarks by rating."""
    from services.intelligence_engine import PRICING_BENCHMARKS, FEE_SCHEDULE
    return _ok({"benchmarks": PRICING_BENCHMARKS, "fees": FEE_SCHEDULE})
