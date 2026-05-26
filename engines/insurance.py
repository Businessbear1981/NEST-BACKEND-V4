"""
NEST Insurance Surety Module — Silo 8
Carrier submission packages + IFS rating cap validation.
Extends existing SuretyEngine from services/core.py.
"""
from services.core import SuretyEngine, check_ltv
from datetime import datetime

base_surety = SuretyEngine()

# Full carrier whitelist with IFS ratings (refresh quarterly)
CARRIER_WHITELIST = [
    {"name": "Berkshire Hathaway", "moodys": "Aa1", "sp": "AA+", "max_bond": 1_000_000_000, "specialty": ["performance", "payment"]},
    {"name": "Liberty Mutual", "moodys": "A2", "sp": "A", "max_bond": 500_000_000, "specialty": ["dual_wrap", "performance"]},
    {"name": "Travelers", "moodys": "Aa2", "sp": "AA", "max_bond": 750_000_000, "specialty": ["payment", "performance"]},
    {"name": "Zurich", "moodys": "Aa3", "sp": "AA-", "max_bond": 600_000_000, "specialty": ["performance", "builders_risk"]},
    {"name": "Chubb", "moodys": "Aa3", "sp": "AA", "max_bond": 800_000_000, "specialty": ["performance", "payment"]},
    {"name": "The Hartford", "moodys": "A1", "sp": "A+", "max_bond": 400_000_000, "specialty": ["payment"]},
    {"name": "CNA", "moodys": "A2", "sp": "A", "max_bond": 300_000_000, "specialty": ["performance"]},
    {"name": "Nationwide", "moodys": "A1", "sp": "A+", "max_bond": 350_000_000, "specialty": ["performance", "completion"]},
]

RATING_NUMERIC = {
    "Aaa": 1, "Aa1": 2, "Aa2": 3, "Aa3": 4, "A1": 5, "A2": 6, "A3": 7,
    "Baa1": 8, "Baa2": 9, "Baa3": 10, "Ba1": 11,
}


def wrap_rating_cap(unwrapped_rating: str, carrier_ifs: str) -> str:
    """Wrapped tranche rating = min(unwrapped, carrier IFS)."""
    u = RATING_NUMERIC.get(unwrapped_rating, 10)
    c = RATING_NUMERIC.get(carrier_ifs, 10)
    best = min(u, c)
    reverse = {v: k for k, v in RATING_NUMERIC.items()}
    return reverse.get(best, unwrapped_rating)


def recommend_carriers(deal: dict, target_rating: str = "A2") -> dict:
    """Match deal to eligible carriers based on bond size + target rating."""
    face = deal.get("bond_face_usd", deal.get("a_tranche_usd", 0))
    target_num = RATING_NUMERIC.get(target_rating, 6)

    eligible = []
    for carrier in CARRIER_WHITELIST:
        ifs_num = RATING_NUMERIC.get(carrier["moodys"], 10)
        if carrier["max_bond"] >= face and ifs_num <= target_num + 2:
            capped = wrap_rating_cap(target_rating, carrier["moodys"])
            eligible.append({
                **carrier,
                "capped_rating": capped,
                "achieves_target": RATING_NUMERIC.get(capped, 10) <= target_num,
            })

    eligible.sort(key=lambda x: RATING_NUMERIC.get(x["moodys"], 10))

    return {
        "deal_id": deal.get("id", ""),
        "bond_face": round(face),
        "target_rating": target_rating,
        "eligible_carriers": eligible,
        "recommended": eligible[0]["name"] if eligible else "No eligible carrier",
        "total_eligible": len(eligible),
        "assessed_at": datetime.utcnow().isoformat(),
    }
