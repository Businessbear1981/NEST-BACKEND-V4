"""
NEST Rating, ESG, Climate, Covenant, and Trustee Routes.
Supporting modules for the BondCommandCenter.
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth
from datetime import datetime
from services.auth import require_auth

rating_esg_bp = Blueprint("rating_esg", __name__)


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


# ══════════════════════════════════════════════════════════════════
# RATING INTELLIGENCE
# ══════════════════════════════════════════════════════════════════

@rating_esg_bp.route("/rating/assess", methods=["POST"])
def rating_assess():
    b = request.get_json() or {}
    from engines.maxwell_engine import score_deal
    from services.core import CreditEngine

    maxwell = score_deal(b)
    credit = CreditEngine().compute(b)

    from services.ai_router import plugin_hub
    prompt = (
        f"Provide a 3-sentence rating rationale for a bond with: "
        f"DSCR {credit['dscr']}x, LTV {credit['ltv_pct']}%, "
        f"indicative rating {maxwell['indicative_rating']}, "
        f"deal score {credit['deal_score']}/100. "
        f"Reference Moody's/S&P methodology. Jimmy Lee tone."
    )
    ai = plugin_hub.route("credit_memo", prompt)

    return _ok({
        "maxwell": maxwell,
        "credit_metrics": credit,
        "ai_rationale": ai.get("content", "") if ai.get("success") else "",
        "indicative_rating": maxwell["indicative_rating"],
        "deal_score": credit["deal_score"],
        "deal_score_grade": credit["deal_score_grade"],
    })


@rating_esg_bp.route("/rating/compare", methods=["POST"])
def rating_compare():
    b = request.get_json() or {}
    from services.core import JPM, CreditEngine
    credit = CreditEngine().compute(b)

    comparison = {}
    for grade, bench in JPM.items():
        comparison[grade] = {
            "dscr": {"required": bench["dscr"], "actual": credit["dscr"],
                     "pass": credit["dscr"] >= bench["dscr"]},
            "ltv": {"required": bench["ltv"], "actual": credit["ltv_pct"],
                    "pass": credit["ltv_pct"] <= bench["ltv"]},
            "cf_leverage": {"required": bench["cf"], "actual": credit["cash_flow_leverage"],
                           "pass": credit["cash_flow_leverage"] <= bench["cf"]},
            "de_ratio": {"required": bench["de"], "actual": credit["debt_to_ebitda"],
                        "pass": credit["debt_to_ebitda"] <= bench["de"]},
        }

    return _ok({"comparison": comparison, "current_grade": credit["obligor_grade"]})


# ══════════════════════════════════════════════════════════════════
# ESG SCORING
# ══════════════════════════════════════════════════════════════════

ESG_CRITERIA = {
    "environmental": {
        "energy_efficiency": {"weight": 25, "desc": "LEED/Energy Star certification"},
        "water_management": {"weight": 15, "desc": "Water recycling & conservation"},
        "emissions_reduction": {"weight": 10, "desc": "Scope 1+2 emissions tracking"},
    },
    "social": {
        "community_impact": {"weight": 15, "desc": "Local employment & services"},
        "resident_wellbeing": {"weight": 10, "desc": "Health & wellness programs"},
        "workforce_standards": {"weight": 10, "desc": "Living wage & benefits"},
    },
    "governance": {
        "board_diversity": {"weight": 5, "desc": "Board composition"},
        "transparency": {"weight": 5, "desc": "Reporting & disclosure quality"},
        "compliance_history": {"weight": 5, "desc": "Regulatory track record"},
    },
}


@rating_esg_bp.route("/esg/score", methods=["POST"])
def esg_score():
    b = request.get_json() or {}
    scores_input = b.get("scores", {})

    pillar_scores = {}
    total_weighted = 0
    total_weight = 0

    for pillar, criteria in ESG_CRITERIA.items():
        pillar_total = 0
        pillar_weight = 0
        details = {}
        for criterion, meta in criteria.items():
            raw = scores_input.get(criterion, 50)
            weighted = raw * meta["weight"] / 100
            pillar_total += weighted
            pillar_weight += meta["weight"]
            details[criterion] = {
                "score": raw, "weight": meta["weight"],
                "weighted": round(weighted, 1), "desc": meta["desc"],
            }
        pillar_pct = round(pillar_total / pillar_weight * 100, 1) if pillar_weight else 0
        pillar_scores[pillar] = {"score": pillar_pct, "details": details}
        total_weighted += pillar_total
        total_weight += pillar_weight

    composite = round(total_weighted / total_weight * 100, 1) if total_weight else 0
    grade = "A" if composite >= 80 else "B" if composite >= 65 else "C" if composite >= 50 else "D"

    return _ok({
        "composite_score": composite,
        "esg_grade": grade,
        "pillar_scores": pillar_scores,
        "criteria": ESG_CRITERIA,
        "bond_impact": "Green bond eligible" if composite >= 75 else "Standard bond",
    })


# ══════════════════════════════════════════════════════════════════
# CLIMATE RESILIENCE
# ══════════════════════════════════════════════════════════════════

@rating_esg_bp.route("/climate/assess", methods=["POST"])
def climate_assess():
    b = request.get_json() or {}
    state = b.get("state", "FL")

    physical_risk = {
        "FL": {"flood": 85, "hurricane": 90, "wildfire": 10, "earthquake": 5, "heat_stress": 70},
        "CA": {"flood": 40, "hurricane": 5, "wildfire": 80, "earthquake": 75, "heat_stress": 60},
        "TX": {"flood": 65, "hurricane": 70, "wildfire": 30, "earthquake": 10, "heat_stress": 80},
        "AZ": {"flood": 25, "hurricane": 5, "wildfire": 55, "earthquake": 15, "heat_stress": 95},
        "WA": {"flood": 45, "hurricane": 5, "wildfire": 40, "earthquake": 60, "heat_stress": 25},
    }.get(state, {"flood": 50, "hurricane": 50, "wildfire": 50, "earthquake": 50, "heat_stress": 50})

    physical_composite = sum(physical_risk.values()) / len(physical_risk)

    transition_risk = {
        "regulatory_change": 45, "carbon_pricing": 30,
        "technology_shift": 35, "market_preference": 40,
    }
    transition_composite = sum(transition_risk.values()) / len(transition_risk)

    insurance_premium_adj = 1.0 + (physical_composite / 100) * 0.35
    resilience_score = max(0, 100 - int((physical_composite + transition_composite) / 2))

    mitigations = []
    if physical_risk.get("flood", 0) > 60:
        mitigations.append({"risk": "flood", "action": "Flood insurance + elevated construction", "priority": "high"})
    if physical_risk.get("hurricane", 0) > 60:
        mitigations.append({"risk": "hurricane", "action": "Impact-rated windows + backup power", "priority": "high"})
    if physical_risk.get("wildfire", 0) > 60:
        mitigations.append({"risk": "wildfire", "action": "Defensible space + fire-resistant materials", "priority": "high"})
    if physical_risk.get("heat_stress", 0) > 70:
        mitigations.append({"risk": "heat_stress", "action": "Enhanced HVAC + shading design", "priority": "medium"})
    if physical_risk.get("earthquake", 0) > 50:
        mitigations.append({"risk": "earthquake", "action": "Seismic retrofitting required", "priority": "high"})

    return _ok({
        "state": state,
        "physical_risk": physical_risk,
        "physical_composite": round(physical_composite, 1),
        "transition_risk": transition_risk,
        "transition_composite": round(transition_composite, 1),
        "resilience_score": resilience_score,
        "insurance_premium_multiplier": round(insurance_premium_adj, 3),
        "rating_impact": "Negative watch" if physical_composite > 70 else "Neutral",
        "recommended_mitigations": mitigations,
    })


# ══════════════════════════════════════════════════════════════════
# COVENANT MONITORING
# ══════════════════════════════════════════════════════════════════

@rating_esg_bp.route("/covenants/monitor", methods=["POST"])
def covenant_monitor():
    b = request.get_json() or {}
    covenants = b.get("covenants", [])

    results = []
    breaches = 0
    for cov in covenants:
        threshold = float(cov.get("threshold", 0))
        current = float(cov.get("current", 0))
        cov_type = cov.get("type", "minimum")

        if cov_type == "minimum":
            compliant = current >= threshold
            headroom = current - threshold
        else:
            compliant = current <= threshold
            headroom = threshold - current

        if not compliant:
            breaches += 1

        results.append({
            "name": cov.get("name", ""),
            "type": cov_type,
            "threshold": threshold,
            "current": current,
            "compliant": compliant,
            "headroom": round(headroom, 3),
            "status": "compliant" if compliant else "breach",
            "severity": "critical" if not compliant and abs(headroom) > threshold * 0.1 else "warning" if not compliant else "ok",
        })

    return _ok({
        "covenants": results,
        "total": len(results),
        "compliant": len(results) - breaches,
        "breaches": breaches,
        "overall_status": "breach" if breaches > 0 else "compliant",
    })


# ══════════════════════════════════════════════════════════════════
# TRUSTEE MANAGEMENT
# ══════════════════════════════════════════════════════════════════

TRUSTEE_TASKS = [
    {"id": "t1", "task": "Bond indenture review & execution", "phase": "pre-issuance", "status": "pending"},
    {"id": "t2", "task": "Paying agent agreement", "phase": "pre-issuance", "status": "pending"},
    {"id": "t3", "task": "Escrow account setup", "phase": "pre-issuance", "status": "pending"},
    {"id": "t4", "task": "CUSIP/ISIN registration", "phase": "pre-issuance", "status": "pending"},
    {"id": "t5", "task": "DTC eligibility confirmation", "phase": "pre-issuance", "status": "pending"},
    {"id": "t6", "task": "Coupon payment processing", "phase": "post-issuance", "status": "pending"},
    {"id": "t7", "task": "Sinking fund administration", "phase": "post-issuance", "status": "pending"},
    {"id": "t8", "task": "Bondholder communication", "phase": "post-issuance", "status": "pending"},
    {"id": "t9", "task": "Annual compliance certification", "phase": "ongoing", "status": "pending"},
    {"id": "t10", "task": "Event of default monitoring", "phase": "ongoing", "status": "pending"},
]


@rating_esg_bp.route("/trustee/tasks", methods=["GET"])

def trustee_tasks():
    phase = request.args.get("phase")
    tasks = TRUSTEE_TASKS if not phase else [t for t in TRUSTEE_TASKS if t["phase"] == phase]
    completed = sum(1 for t in tasks if t["status"] == "completed")
    return _ok({
        "tasks": tasks,
        "total": len(tasks),
        "completed": completed,
        "completion_pct": round(completed / len(tasks) * 100) if tasks else 0,
    })


@rating_esg_bp.route("/trustee/tasks/<task_id>", methods=["PATCH"])
def update_trustee_task(task_id):
    b = request.get_json() or {}
    task = next((t for t in TRUSTEE_TASKS if t["id"] == task_id), None)
    if not task:
        return _err("Task not found", 404)
    task["status"] = b.get("status", task["status"])
    return _ok(task)


# ══════════════════════════════════════════════════════════════════
# RMA BENCHMARK
# ══════════════════════════════════════════════════════════════════

RMA_BENCHMARKS = {
    "6232": {
        "current_ratio": 1.8, "debt_to_equity": 2.5, "profit_margin_pct": 12,
        "occupancy_pct": 88, "revenue_per_unit": 65_000, "opex_ratio": 0.72,
    },
    "6231": {
        "current_ratio": 1.5, "debt_to_equity": 3.0, "profit_margin_pct": 8,
        "occupancy_pct": 85, "revenue_per_unit": 85_000, "opex_ratio": 0.78,
    },
    "5311": {
        "current_ratio": 2.0, "debt_to_equity": 2.0, "profit_margin_pct": 18,
        "occupancy_pct": 92, "revenue_per_unit": 42_000, "opex_ratio": 0.65,
    },
}


@rating_esg_bp.route("/rma/benchmark", methods=["POST"])
def rma_benchmark():
    b = request.get_json() or {}
    naics = b.get("naics", "6232")
    bench = RMA_BENCHMARKS.get(naics, RMA_BENCHMARKS["6232"])

    actuals = b.get("actuals", {})
    comparison = {}
    for metric, benchmark_val in bench.items():
        actual_val = actuals.get(metric, benchmark_val)
        if "debt" in metric or "opex" in metric:
            delta = benchmark_val - actual_val
        else:
            delta = actual_val - benchmark_val
        better = delta >= 0

        comparison[metric] = {
            "benchmark": benchmark_val,
            "actual": actual_val,
            "delta": round(delta, 2),
            "status": "above" if better else "below",
        }

    return _ok({"naics": naics, "benchmarks": bench, "comparison": comparison})
