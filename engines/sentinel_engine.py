"""
NEST Sentinel Risk Engine — Silo 5
8-dimension risk scoring per Moody's capabilities mirror.
Extends existing RiskEngine from services/core.py with 8th dimension + catastrophe modeling.
"""
from services.core import RiskEngine, check_ltv
from datetime import datetime

base_risk = RiskEngine()

# Extended to 8 dimensions (original had 7)
DIMENSIONS_8 = {
    "counterparty":   {"weight": 0.15, "desc": "Sponsor, GC, EPC, O&M, offtaker, manager credit quality"},
    "cash_flow":      {"weight": 0.15, "desc": "DSCR + LTV + leverage stability"},
    "physical":       {"weight": 0.15, "desc": "Hurricane, flood, seismic, fire — catastrophe modeling"},
    "transition":     {"weight": 0.10, "desc": "Regulatory, zoning, licensing (AHCA for senior living)"},
    "cyber":          {"weight": 0.05, "desc": "Operational technology risk for issuer entity"},
    "fx":             {"weight": 0.05, "desc": "Cross-currency exposure"},
    "construction":   {"weight": 0.20, "desc": "Cost + schedule + GC quality (construction deals only)"},
    "refinancing":    {"weight": 0.15, "desc": "Balloon maturity, market access, rate environment"},
}

FEMA_FLOOD_ZONES = {"A": 20, "AE": 25, "V": 10, "VE": 5, "X": 80, "X500": 70}
HURRICANE_ZONES = {"coastal_high_hazard": 15, "wind_borne_debris": 30, "inland": 70, "none": 90}


def assess_physical_risk(deal: dict) -> dict:
    """Catastrophe modeling — hurricane, flood, seismic, fire."""
    flood = FEMA_FLOOD_ZONES.get(deal.get("fema_flood_zone", "X"), 70)
    hurricane = HURRICANE_ZONES.get(deal.get("hurricane_zone", "none"), 90)
    seismic = deal.get("seismic_score", 85)
    fire = deal.get("wildfire_score", 90)
    composite = round(flood * 0.3 + hurricane * 0.3 + seismic * 0.2 + fire * 0.2)
    return {
        "flood_score": flood,
        "hurricane_score": hurricane,
        "seismic_score": seismic,
        "fire_score": fire,
        "composite": composite,
        "level": "green" if composite >= 70 else "yellow" if composite >= 45 else "red",
    }


def assess_refinancing_risk(deal: dict) -> dict:
    """Balloon maturity and market access risk."""
    years_to_maturity = deal.get("years_to_maturity", 10)
    has_extension = deal.get("extension_option", False)
    market_access = deal.get("market_access_score", 70)
    score = market_access
    if years_to_maturity <= 2:
        score -= 20
    elif years_to_maturity <= 5:
        score -= 5
    if has_extension:
        score += 10
    score = max(0, min(100, score))
    return {
        "score": score,
        "years_to_maturity": years_to_maturity,
        "has_extension": has_extension,
        "level": "green" if score >= 70 else "yellow" if score >= 45 else "red",
    }


def full_risk_assessment(deal: dict, metrics: dict) -> dict:
    """
    Full 8-dimension risk assessment.
    Returns composite score + per-dimension breakdown + recommended actions.
    """
    # Get base 7-dim from existing engine
    base = base_risk.score_deal(deal, metrics)
    scores = base["dimension_scores"]

    # Add physical risk (catastrophe)
    phys = assess_physical_risk(deal)
    scores["physical"] = {"score": phys["composite"], "level": phys["level"], "detail": phys}

    # Add refinancing risk (8th dimension)
    refi = assess_refinancing_risk(deal)
    scores["refinancing"] = {"score": refi["score"], "level": refi["level"], "detail": refi}

    # Recompute composite with 8 dimensions
    composite = sum(
        scores.get(dim, {}).get("score", 50) * info["weight"]
        for dim, info in DIMENSIONS_8.items()
    )
    level = ("green" if composite >= 70 else "yellow" if composite >= 45
             else "red" if composite >= 25 else "critical")

    # Is construction deal?
    if not deal.get("is_construction"):
        scores.pop("construction", None)

    return {
        "composite_score": round(composite, 1),
        "risk_level": level,
        "dimensions": DIMENSIONS_8,
        "dimension_scores": scores,
        "ltv_risk": check_ltv(metrics.get("ltv_pct", 0)),
        "recommended_actions": base.get("recommended_actions", []),
        "assessment_date": datetime.utcnow().isoformat(),
    }
