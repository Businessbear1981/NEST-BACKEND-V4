"""
NEST Intake Engine — Silo 1
Pod Code + Permit Management.
Entry point for every deal. No deal moves downstream until intake is complete.
"""
from datetime import datetime
from services.core import NAICS

# Pod Code format: STATE-COUNTY_CODE-ASSET_TYPE
# e.g., FL-VEN-CCRC (Life Star Pointe), FL-SAR-LP (Jacaranda)
ASSET_TYPES = {
    "CCRC": "Continuing Care Retirement Community",
    "LP": "Life Plan Community",
    "ALF": "Assisted Living Facility",
    "SNF": "Skilled Nursing Facility",
    "MF": "Multifamily",
    "HOTEL": "Hospitality",
    "OFFICE": "Office",
    "RETAIL": "Retail",
    "INDUST": "Industrial",
    "INFRA": "Infrastructure",
    "MIXED": "Mixed-Use",
}

PERMIT_TYPES = [
    "zoning_approval",
    "building_permit",
    "environmental_clearance",
    "sector_license",       # e.g., AHCA for senior living in FL
    "hurricane_compliance", # coastal zones
    "fire_marshal",
    "utility_connection",
    "traffic_study",
]


def classify_deal(state: str, county_code: str, asset_type: str,
                  naics_code: str = None) -> dict:
    """Generate Pod Code and classify deal."""
    pod_code = f"{state}-{county_code}-{asset_type}".upper()
    asset_desc = ASSET_TYPES.get(asset_type.upper(), "Unknown")
    naics_desc = NAICS.get(naics_code, "Not classified") if naics_code else None

    regulatory_overlay = []
    if asset_type.upper() in ("CCRC", "LP", "ALF", "SNF"):
        regulatory_overlay.append("State health department licensing required")
        if state == "FL":
            regulatory_overlay.append("AHCA (Agency for Health Care Administration) license")
    if state == "FL":
        regulatory_overlay.append("Florida Building Code — hurricane compliance")

    return {
        "pod_code": pod_code,
        "state": state,
        "county_code": county_code,
        "asset_type": asset_type.upper(),
        "asset_description": asset_desc,
        "naics_code": naics_code,
        "naics_description": naics_desc,
        "regulatory_overlay": regulatory_overlay,
        "classified_at": datetime.utcnow().isoformat(),
    }


def create_permit_checklist(pod_code: str, deal_data: dict = None) -> dict:
    """Generate required permits based on Pod Code."""
    parts = pod_code.split("-")
    state = parts[0] if len(parts) >= 1 else ""
    asset_type = parts[2] if len(parts) >= 3 else ""

    permits = []
    for pt in PERMIT_TYPES:
        required = True
        if pt == "hurricane_compliance" and state not in ("FL", "TX", "LA", "NC", "SC"):
            required = False
        if pt == "sector_license" and asset_type not in ("CCRC", "LP", "ALF", "SNF"):
            required = False

        permits.append({
            "type": pt,
            "required": required,
            "status": "not_started",
            "issuer": None,
            "deadline": None,
            "blocking": required,
            "notes": "",
        })

    required_count = sum(1 for p in permits if p["required"])
    completed = sum(1 for p in permits if p["status"] == "approved")

    return {
        "pod_code": pod_code,
        "permits": permits,
        "total_required": required_count,
        "completed": completed,
        "completion_pct": round(completed / required_count * 100) if required_count > 0 else 0,
        "shovel_ready": completed == required_count,
    }
