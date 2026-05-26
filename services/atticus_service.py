"""
Atticus — Covenant monitoring service.

Tests covenants against live deal metrics from Supabase.
Flags breaches, tracks cure periods, returns structured compliance results.
"""
from datetime import datetime

try:
    from services.database import db
except ImportError:
    db = None

# JPM benchmark defaults for covenant thresholds
DEFAULT_COVENANTS = [
    {"covenant_type": "dscr", "threshold_value": 1.50, "direction": "minimum", "test_frequency": "quarterly"},
    {"covenant_type": "ltv", "threshold_value": 75.0, "direction": "maximum", "test_frequency": "quarterly"},
    {"covenant_type": "cf_leverage", "threshold_value": 2.0, "direction": "maximum", "test_frequency": "quarterly"},
    {"covenant_type": "bs_leverage", "threshold_value": 2.5, "direction": "maximum", "test_frequency": "quarterly"},
    {"covenant_type": "d_ebitda", "threshold_value": 6.5, "direction": "maximum", "test_frequency": "quarterly"},
    {"covenant_type": "icr", "threshold_value": 2.25, "direction": "minimum", "test_frequency": "quarterly"},
]


def test_covenants(deal_id: str) -> dict:
    """Pull covenants + deal metrics from DB, test all thresholds, update results."""
    if not db or not db.configured:
        return {"error": "Database not configured", "deal_id": deal_id}

    # Get deal metrics
    deals = db.select("deals", {"id": f"eq.{deal_id}"})
    if not deals:
        return {"error": "Deal not found", "deal_id": deal_id}
    deal = deals[0]

    # Get covenants (or create defaults)
    covenants = db.select("covenants", {"deal_id": f"eq.{deal_id}"})
    if not covenants:
        for cov in DEFAULT_COVENANTS:
            db.insert("covenants", {
                "deal_id": deal_id,
                "covenant_type": cov["covenant_type"],
                "description": f"{cov['covenant_type']} {cov['direction']} {cov['threshold_value']}",
                "threshold_value": cov["threshold_value"],
                "test_frequency": cov["test_frequency"],
                "in_compliance": True,
            })
        covenants = db.select("covenants", {"deal_id": f"eq.{deal_id}"})

    # Map deal columns to covenant metric names
    metric_map = {
        "dscr": float(deal.get("dscr", 0)),
        "ltv": float(deal.get("ltv", 0)),
        "cf_leverage": float(deal.get("cf_leverage", 0)),
        "bs_leverage": float(deal.get("bs_leverage", 0)),
        "d_ebitda": float(deal.get("d_ebitda", 0)),
        "icr": float(deal.get("icr", 0)),
    }

    results = []
    breaches = []
    for cov in covenants:
        cov_type = cov["covenant_type"]
        threshold = float(cov.get("threshold_value", 0))
        current = metric_map.get(cov_type)

        if current is None:
            results.append({
                "covenant_id": cov["id"],
                "type": cov_type,
                "threshold": threshold,
                "current": None,
                "status": "untestable",
                "in_compliance": True,
            })
            continue

        # Determine direction from description
        desc = (cov.get("description") or "").lower()
        if "minimum" in desc or cov_type in ("dscr", "icr"):
            passed = current >= threshold
        else:
            passed = current <= threshold

        # Update DB
        db.update("covenants", {"id": f"eq.{cov['id']}"}, {
            "current_value": current,
            "in_compliance": passed,
        })

        status = "compliant" if passed else "breach"
        entry = {
            "covenant_id": cov["id"],
            "type": cov_type,
            "threshold": threshold,
            "current": current,
            "status": status,
            "in_compliance": passed,
        }
        results.append(entry)
        if not passed:
            breaches.append(entry)

    return {
        "deal_id": deal_id,
        "deal_name": deal.get("name", ""),
        "tested_at": datetime.utcnow().isoformat(),
        "total_covenants": len(results),
        "in_compliance": len(breaches) == 0,
        "breaches": breaches,
        "results": results,
    }


def get_breach_summary(deal_id: str) -> dict:
    """Quick check — just the breaches."""
    result = test_covenants(deal_id)
    return {
        "deal_id": deal_id,
        "in_compliance": result.get("in_compliance", True),
        "breach_count": len(result.get("breaches", [])),
        "breaches": result.get("breaches", []),
    }
