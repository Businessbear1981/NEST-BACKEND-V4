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


@intel_engine_bp.post("/rating-analysis")
def full_rating_analysis():
    """Run complete S&P + Moody's analysis with ALL published ratio benchmarks.

    Body: full financial data dict with ratios (ffo_to_debt, debt_to_ebitda, etc.)
    Returns: S&P financial risk profile, Moody's metric scores, predicted rating,
    structuring targets, data completeness checklist.

    CTO NOTE: This endpoint uses confirmed published benchmarks from
    rating_benchmarks.py. The scoring functions apply the exact thresholds
    S&P and Moody's publish in their methodology documents.
    """
    body = request.get_json(silent=True) or {}
    result = _engine().full_rating_analysis(body)
    return _ok(result)


@intel_engine_bp.post("/optimize")
def optimize_structure():
    """Run structuring scenarios and compare rating outcomes.

    Body: { financials: {...}, scenarios: [{name, changes}, ...] }
    If scenarios not provided, runs 5 default scenarios:
    - Base case
    - Add bond insurance
    - Add cash-collateralized LC
    - Increase equity to 35%
    - Tighten DSCR covenant

    Returns: array of scenarios with predicted rating for each.

    CTO NOTE: This is the bond optimization engine. It runs the same
    S&P/Moody's scoring against multiple structural variations to show
    which structure produces the best rating at the lowest cost.
    """
    body = request.get_json(silent=True) or {}
    financials = body.get("financials", body)
    scenarios = body.get("scenarios")
    result = _engine().optimize_structure(financials, scenarios)
    return _ok(result)


@intel_engine_bp.get("/benchmarks")
def rating_benchmarks_endpoint():
    """Return the full S&P and Moody's benchmark tables.

    CTO NOTE: These are the REAL published benchmarks, not approximations.
    S&P FFO/Debt, Debt/EBITDA thresholds for all 6 financial risk categories.
    Moody's Debt/EBITDA, RCF/Net Debt, (EBITDA-Capex)/Interest for Aaa-Ca.
    Source: public agency methodology documents.
    """
    from services.rating_benchmarks import (
        SP_FINANCIAL_RISK_BENCHMARKS,
        MOODYS_FINANCIAL_METRICS,
        SP_ANCHOR_MATRIX,
        STRUCTURING_CRITERIA,
        REQUIRED_FINANCIAL_DATA,
    )
    return _ok({
        "sp": {
            "financial_risk_benchmarks": SP_FINANCIAL_RISK_BENCHMARKS,
            "anchor_matrix": {f"{k[0]},{k[1]}": v for k, v in SP_ANCHOR_MATRIX.items()},
        },
        "moodys": {
            "financial_metrics": MOODYS_FINANCIAL_METRICS,
        },
        "structuring_criteria": STRUCTURING_CRITERIA,
        "required_financial_data": REQUIRED_FINANCIAL_DATA,
    })


@intel_engine_bp.get("/required-data")
def required_data():
    """Return the complete list of financial data needed from clients.

    CTO NOTE: This drives the Roots document ingestion checklist.
    Every ratio here needs to be extracted from client financials.
    Same data feeds the credit memo, the rating pre-score, and
    the structuring engine. One data schema, three consumers.
    """
    from services.rating_benchmarks import REQUIRED_FINANCIAL_DATA
    return _ok(REQUIRED_FINANCIAL_DATA)
