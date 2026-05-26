"""NEST Engine Routes — Exposes all 11 domain engines via REST API.
Wire the Modeling Module, Maxwell, Architect, PricingEngine, Sentinel,
Insurance, Intake, Audit, Placement, and Bridge engines to the frontend.
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth
from datetime import datetime, date

engines_bp = Blueprint("engines", __name__)


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


# ── MODELING MODULE (Silo 3) ─────────────────────────────────────

from engines.modeling import (
    compute_noi, compute_ebitda, compute_dscr, compute_leverage,
    compute_ccsr, compute_pata, compute_entrance_fee_velocity,
    compute_principal_sweep, compute_construction_amortization,
    run_stress_scenario,
)


@engines_bp.route("/modeling/noi", methods=["POST"])
@require_auth()
def modeling_noi():
    b = request.get_json() or {}
    return _ok(compute_noi(b.get("revenue", 0), b.get("opex", 0)))


@engines_bp.route("/modeling/ebitda", methods=["POST"])
@require_auth()
def modeling_ebitda():
    b = request.get_json() or {}
    return _ok(compute_ebitda(b.get("noi", 0), b.get("management_fee", 0),
                              b.get("reserve_contribution", 0)))


@engines_bp.route("/modeling/dscr", methods=["POST"])
@require_auth()
def modeling_dscr():
    b = request.get_json() or {}
    return _ok(compute_dscr(b.get("noi", 0), b.get("annual_debt_service", 0),
                             b.get("scenario", "base")))


@engines_bp.route("/modeling/leverage", methods=["POST"])
@require_auth()
def modeling_leverage():
    b = request.get_json() or {}
    return _ok(compute_leverage(
        b.get("total_debt", 0), b.get("noi", 0), b.get("equity", 0),
        b.get("ebitda", 0), b.get("appraised_value", 0)))


@engines_bp.route("/modeling/ccsr", methods=["POST"])
@require_auth()
def modeling_ccsr():
    b = request.get_json() or {}
    return _ok(compute_ccsr(
        b.get("cash_on_hand", 0), b.get("debt_service_next_12mo", 0),
        b.get("operating_reserves", 0), b.get("restricted_cash", 0)))


@engines_bp.route("/modeling/pata", methods=["POST"])
@require_auth()
def modeling_pata():
    b = request.get_json() or {}
    return _ok(compute_pata(
        b.get("gross_revenue", 0), b.get("operating_expenses", 0),
        b.get("tax_rate", 0.21), b.get("amortization", 0),
        b.get("interest_expense", 0)))


@engines_bp.route("/modeling/entrance-fee-velocity", methods=["POST"])
@require_auth()
def modeling_ef_velocity():
    b = request.get_json() or {}
    return _ok(compute_entrance_fee_velocity(
        b.get("total_units", 0), b.get("turnover_units", 0),
        b.get("gross_fees", 0), b.get("refunds", 0),
        b.get("period_label", "annual")))


@engines_bp.route("/modeling/principal-sweep", methods=["POST"])
@require_auth()
def modeling_sweep():
    b = request.get_json() or {}
    return _ok(compute_principal_sweep(
        b.get("beginning_balance", 0), b.get("net_cash_flow", 0),
        b.get("sweep_pct", 1.0), b.get("minimum_balance", 0)))


@engines_bp.route("/modeling/construction-amortization", methods=["POST"])
@require_auth()
def modeling_construction():
    b = request.get_json() or {}
    return _ok(compute_construction_amortization(
        b.get("total_budget", 0), b.get("draws", []),
        b.get("contingency_pct", 0.05)))


@engines_bp.route("/modeling/stress", methods=["POST"])
@require_auth()
def modeling_stress():
    b = request.get_json() or {}
    return _ok(run_stress_scenario(
        b.get("base_noi", 0), b.get("base_debt_service", 0),
        b.get("total_debt", 0), b.get("scenario", "base")))


@engines_bp.route("/modeling/full-run", methods=["POST"])
@require_auth()
def modeling_full_run():
    """Run all Modeling Module views for a deal at once."""
    b = request.get_json() or {}
    revenue = b.get("revenue", 0)
    opex = b.get("opex", 0)
    mgmt_fee = b.get("management_fee", 0)
    reserve = b.get("reserve_contribution", 0)
    total_debt = b.get("total_debt", 0)
    equity = b.get("equity", 0)
    appraised = b.get("appraised_value", 0)
    ds = b.get("annual_debt_service", 0)

    noi_result = compute_noi(revenue, opex)
    noi = noi_result["noi"]
    ebitda_result = compute_ebitda(noi, mgmt_fee, reserve)
    ebitda = ebitda_result["ebitda"]

    return _ok({
        "noi": noi_result,
        "ebitda": ebitda_result,
        "dscr": compute_dscr(noi, ds),
        "leverage": compute_leverage(total_debt, noi, equity, ebitda, appraised),
        "stress": run_stress_scenario(noi, ds, total_debt),
    })


# ── MAXWELL SCORING ENGINE (Silo 4) ─────────────────────────────

from engines.maxwell_engine import score_deal as maxwell_score


@engines_bp.route("/maxwell/score", methods=["POST"])
@require_auth()
def maxwell_score_deal():
    b = request.get_json() or {}
    return _ok(maxwell_score(b))


# ── ARCHITECT STRUCTURING ENGINE (Silo 6) ────────────────────────

from engines.architect import generate_candidates


@engines_bp.route("/architect/candidates", methods=["POST"])
@require_auth()
def architect_candidates():
    b = request.get_json() or {}
    return _ok(generate_candidates(b, b.get("target_rating", "A")))


# ── PRICING ENGINE (Silo 7) ─────────────────────────────────────

from engines.pricing import (
    price_bond, hedge_adjusted_yield, is_index_eligible,
    yield_to_worst, spread_to_benchmark,
    day_count_fraction, accrued_interest, market_value,
    interest_return, price_return, total_return, total_unhedged_return,
    security_weight,
)


@engines_bp.route("/pricing/bond", methods=["POST"])
@require_auth()
def pricing_bond():
    b = request.get_json() or {}
    lcd = b.get("last_coupon_date")
    sd = b.get("settlement_date")
    if lcd:
        lcd = date.fromisoformat(lcd)
    if sd:
        sd = date.fromisoformat(sd)
    return _ok(price_bond(
        par=b.get("par", 100_000_000),
        clean_price=b.get("clean_price", 100),
        coupon_rate=b.get("coupon_rate", 0.065),
        ytm=b.get("ytm", 0.07),
        maturity_years=b.get("maturity_years", 10),
        frequency=b.get("frequency", 2),
        last_coupon_date=lcd, settlement_date=sd,
        fx_rate=b.get("fx_rate", 1.0),
        benchmark_ytm=b.get("benchmark_ytm", 0.0428),
        swap_rate=b.get("swap_rate", 0.045),
        convention=b.get("convention", "30/360"),
        rating=b.get("rating", "BBB"),
    ))


@engines_bp.route("/pricing/hedge-adjusted-yield", methods=["POST"])
@require_auth()
def pricing_hedge():
    b = request.get_json() or {}
    return _ok({
        "yield_local": b.get("yield_local", 0),
        "hedge_adjusted_yield": hedge_adjusted_yield(
            b.get("yield_local", 0),
            b.get("forward_rate_30d", 0),
            b.get("fx_spot", 1.0)),
    })


@engines_bp.route("/pricing/index-eligibility", methods=["POST"])
@require_auth()
def pricing_eligibility():
    b = request.get_json() or {}
    return _ok(is_index_eligible(
        b.get("par_outstanding", 0), b.get("rating", "BBB"),
        b.get("maturity_months", 120), b.get("currency", "USD"),
        b.get("country", "US"), b.get("is_convertible", False),
        b.get("is_floating", False)))


@engines_bp.route("/pricing/yield-to-worst", methods=["POST"])
@require_auth()
def pricing_ytw():
    b = request.get_json() or {}
    return _ok({
        "ytm": b.get("ytm", 0),
        "call_yields": b.get("call_yields", []),
        "yield_to_worst": yield_to_worst(b.get("ytm", 0), b.get("call_yields", [])),
    })


# ── SENTINEL RISK ENGINE (Silo 5) ───────────────────────────────

from engines.sentinel_engine import full_risk_assessment, assess_physical_risk


@engines_bp.route("/sentinel/assess", methods=["POST"])
@require_auth()
def sentinel_assess():
    b = request.get_json() or {}
    from services.core import CreditEngine
    metrics = CreditEngine().compute(b)
    return _ok(full_risk_assessment(b, metrics))


@engines_bp.route("/sentinel/physical-risk", methods=["POST"])
@require_auth()
def sentinel_physical():
    b = request.get_json() or {}
    return _ok(assess_physical_risk(b))


# ── INSURANCE SURETY (Silo 8) ───────────────────────────────────

from engines.insurance import recommend_carriers, wrap_rating_cap, CARRIER_WHITELIST


@engines_bp.route("/insurance/carriers", methods=["GET"])
@require_auth()
def insurance_carriers():
    return _ok(CARRIER_WHITELIST)


@engines_bp.route("/insurance/recommend", methods=["POST"])
@require_auth()
def insurance_recommend():
    b = request.get_json() or {}
    return _ok(recommend_carriers(b, b.get("target_rating", "A2")))


@engines_bp.route("/insurance/wrap-cap", methods=["POST"])
@require_auth()
def insurance_wrap_cap():
    b = request.get_json() or {}
    capped = wrap_rating_cap(b.get("unwrapped_rating", "Baa2"),
                              b.get("carrier_ifs", "Aa2"))
    return _ok({"unwrapped": b.get("unwrapped_rating", "Baa2"),
                "carrier_ifs": b.get("carrier_ifs", "Aa2"),
                "capped_rating": capped})


# ── INTAKE (Silo 1) ─────────────────────────────────────────────

from engines.intake import classify_deal as _intake_classify, create_permit_checklist


@engines_bp.route("/intake/classify", methods=["POST"])
@require_auth()
def intake_classify():
    b = request.get_json() or {}
    return _ok(_intake_classify(
        b.get("state", "FL"), b.get("county_code", ""),
        b.get("asset_type", "CCRC"), b.get("naics_code")))


@engines_bp.route("/intake/permits", methods=["POST"])
@require_auth()
def intake_permits():
    b = request.get_json() or {}
    return _ok(create_permit_checklist(b.get("pod_code", "FL-VEN-CCRC"), b))


# ── AUDIT PACKAGE (Silo 9) ──────────────────────────────────────

from engines.audit_package import generate_package as generate_audit_package


@engines_bp.route("/audit-package/generate", methods=["POST"])
@require_auth()
def audit_generate():
    b = request.get_json() or {}
    deal = b.get("deal", b)
    modeling = b.get("modeling_outputs", {})
    maxwell = b.get("maxwell_output")
    return _ok(generate_audit_package(deal, modeling, maxwell))


# ── BRIDGE SURVEILLANCE (Silo 14) ───────────────────────────────

from engines.bridge_surveillance import monitor_deal as run_surveillance
from services.auth import require_auth


@engines_bp.route("/bridge/surveillance", methods=["POST"])
@require_auth()
def bridge_surveillance():
    b = request.get_json() or {}
    deal = b.get("deal", b)
    current = b.get("current_metrics", {})
    at_issuance = b.get("at_issuance_metrics")
    return _ok(run_surveillance(deal, current, at_issuance))


# ── FULL PIPELINE RUN ───────────────────────────────────────────

@engines_bp.route("/pipeline/run", methods=["POST"])
@require_auth()
def pipeline_full_run():
    """
    Run the full NEST pipeline for a deal — the live mechanic.
    Atlas → Maxwell + Sentinel (parallel) → Architect → Pricing
    Returns all engine outputs + agent events for the flow visualization.
    """
    b = request.get_json() or {}
    events = []
    ts = datetime.utcnow().isoformat

    def emit(agent, state, payload=None):
        events.append({
            "agent": agent, "state": state,
            "timestamp": ts(), "payload": payload or {}})

    # 1. Intake
    emit("Atlas", "running")
    intake_result = _intake_classify(
        b.get("state", "FL"), b.get("county_code", ""),
        b.get("asset_type", "CCRC"), b.get("naics_code"))
    emit("Atlas", "complete", {"pod_code": intake_result.get("pod_code")})

    # 2. Modeling
    emit("Atlas", "running")
    revenue = b.get("revenue", 0)
    opex = b.get("opex", 0)
    noi_result = compute_noi(revenue, opex)
    noi = noi_result["noi"]
    ebitda_result = compute_ebitda(noi, b.get("management_fee", 0))
    ds = b.get("annual_debt_service", 0)
    dscr_result = compute_dscr(noi, ds)
    emit("Atlas", "complete", {"noi": noi, "dscr": dscr_result["dscr"]})

    # 3. Maxwell + Sentinel (parallel fan-out)
    emit("Maxwell", "running")
    emit("Sentinel", "running")
    maxwell_result = maxwell_score(b)
    from services.core import CreditEngine
    metrics = CreditEngine().compute(b)
    sentinel_result = full_risk_assessment(b, metrics)
    emit("Maxwell", "complete", {
        "indicative_rating": maxwell_result["indicative_rating"]})
    emit("Sentinel", "complete", {
        "risk_level": sentinel_result["risk_level"],
        "composite": sentinel_result["composite_score"]})

    # 4. Architect
    emit("Architect", "running")
    architect_result = generate_candidates(b, b.get("target_rating", "A"))
    emit("Architect", "complete", {
        "candidates": len(architect_result["candidates"]),
        "recommendation": architect_result["recommendation"]})

    # 5. Pricing
    emit("PricingEngine", "running")
    pricing_result = price_bond(
        par=b.get("a_tranche_usd", b.get("total_project_cost_usd", 0) * 0.75),
        clean_price=b.get("clean_price", 100),
        coupon_rate=b.get("a_coupon_pct", 0.065),
        ytm=b.get("ytm", 0.07),
        maturity_years=b.get("maturity_years", 10),
        rating=maxwell_result["indicative_rating"],
    )
    emit("PricingEngine", "complete", {
        "market_value": pricing_result["market_value"],
        "spread_bps": pricing_result["spread_to_treasury_bps"]})

    # 6. Insurance
    emit("SuretyScout", "running")
    insurance_result = recommend_carriers(b, b.get("target_rating", "A2"))
    emit("SuretyScout", "complete", {
        "recommended_carrier": insurance_result["recommended"],
        "eligible_count": insurance_result["total_eligible"]})

    return _ok({
        "deal_id": b.get("id", "pipeline_run"),
        "pipeline_status": "complete",
        "events": events,
        "results": {
            "intake": intake_result,
            "modeling": {
                "noi": noi_result,
                "ebitda": ebitda_result,
                "dscr": dscr_result,
            },
            "maxwell": maxwell_result,
            "sentinel": sentinel_result,
            "architect": architect_result,
            "pricing": pricing_result,
            "insurance": insurance_result,
        },
    })
