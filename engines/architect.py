"""
NEST Architect Structuring Engine — Silo 6
Given a deal + target rating, produce 2-3 candidate structures at different cost profiles.

Algorithm:
1. Run Maxwell on base case → baseline indicative rating
2. Compute notch gap to target
3. Iterate structural levers ranked by cost-efficiency
4. Build three candidates: minimal, moderate, conservative
5. Output all-in cost of capital for each
"""
from services.core import CreditEngine, SuretyEngine
from engines.maxwell_engine import score_deal, SCORE_MAP
from datetime import datetime

credit = CreditEngine()
surety = SuretyEngine()

STRUCTURAL_LEVERS = [
    {"name": "DSCR sizing (reduce debt)", "notch_lift": 1, "cost_bps": 0, "priority": 1},
    {"name": "Cash trap covenant", "notch_lift": 0.5, "cost_bps": 5, "priority": 2},
    {"name": "DSRF expansion to 12mo", "notch_lift": 0.5, "cost_bps": 8, "priority": 3},
    {"name": "Series B subordination", "notch_lift": 1, "cost_bps": 35, "priority": 4},
    {"name": "Construction-period LC", "notch_lift": 0.5, "cost_bps": 25, "priority": 5},
    {"name": "Surety wrap (Hylant)", "notch_lift": 2, "cost_bps": 85, "priority": 6},
    {"name": "Dual wrap (performance + payment)", "notch_lift": 3, "cost_bps": 120, "priority": 7},
]


def _rating_to_numeric(rating: str) -> int:
    """Convert rating string to numeric for gap calculation."""
    mapping = {"A": 6, "BBB+": 8, "BBB": 9, "BBB-": 10, "BB+": 11, "BB": 12, "Sub-IG": 15}
    return mapping.get(rating, 12)


def generate_candidates(deal: dict, target_rating: str = "A") -> dict:
    """
    Generate 2-3 candidate structures with cost-of-capital optimization.
    """
    # Score baseline
    maxwell_result = score_deal(deal)
    baseline_rating = maxwell_result["indicative_rating"]
    baseline_numeric = SCORE_MAP.get(baseline_rating, 9)
    target_numeric = SCORE_MAP.get(target_rating.replace("+", "1").replace("-", "3"), 6)
    gap = baseline_numeric - target_numeric

    # Base credit metrics
    metrics = credit.compute(deal)
    tpc = deal.get("total_project_cost_usd", 0)
    a_tranche = deal.get("a_tranche_usd", tpc * 0.75)

    candidates = []

    # Minimal — cheapest path
    min_levers = []
    remaining_gap = gap
    total_cost = 0
    for lever in STRUCTURAL_LEVERS:
        if remaining_gap <= 0:
            break
        min_levers.append(lever["name"])
        remaining_gap -= lever["notch_lift"]
        total_cost += lever["cost_bps"]

    candidates.append({
        "name": "Minimal Enhancement",
        "levers_applied": min_levers,
        "estimated_rating": target_rating if remaining_gap <= 0 else baseline_rating,
        "achieves_target": remaining_gap <= 0,
        "additional_cost_bps": total_cost,
        "all_in_coupon_bps": deal.get("a_coupon_pct", 7.0) * 100 + total_cost,
        "surety_required": "Surety" in str(min_levers),
    })

    # Moderate — one lever beyond minimum
    mod_levers = min_levers.copy()
    mod_cost = total_cost
    for lever in STRUCTURAL_LEVERS:
        if lever["name"] not in mod_levers:
            mod_levers.append(lever["name"])
            mod_cost += lever["cost_bps"]
            break

    candidates.append({
        "name": "Moderate Enhancement",
        "levers_applied": mod_levers,
        "estimated_rating": target_rating,
        "achieves_target": True,
        "additional_cost_bps": mod_cost,
        "all_in_coupon_bps": deal.get("a_coupon_pct", 7.0) * 100 + mod_cost,
        "surety_required": "Surety" in str(mod_levers),
    })

    # Conservative — full wrap
    cons_levers = [l["name"] for l in STRUCTURAL_LEVERS]
    cons_cost = sum(l["cost_bps"] for l in STRUCTURAL_LEVERS)
    candidates.append({
        "name": "Conservative (Full Wrap)",
        "levers_applied": cons_levers,
        "estimated_rating": "Aa3" if gap <= 3 else target_rating,
        "achieves_target": True,
        "additional_cost_bps": cons_cost,
        "all_in_coupon_bps": deal.get("a_coupon_pct", 7.0) * 100 + cons_cost,
        "surety_required": True,
    })

    return {
        "deal_id": deal.get("id", ""),
        "baseline_rating": baseline_rating,
        "target_rating": target_rating,
        "notch_gap": gap,
        "candidates": candidates,
        "structural_levers_available": STRUCTURAL_LEVERS,
        "recommendation": candidates[0]["name"] if candidates[0]["achieves_target"] else candidates[1]["name"],
        "generated_at": datetime.utcnow().isoformat(),
    }
