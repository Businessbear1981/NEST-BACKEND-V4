"""
NEST Broker Placement Layer — Silo 11
Aggregates all upstream silo outputs into Ziegler-format submission package.
"""
from datetime import datetime


def generate_placement_package(deal: dict, maxwell_output: dict,
                                architect_output: dict, sentinel_output: dict,
                                pricing_output: dict = None,
                                insurance_output: dict = None) -> dict:
    """Aggregate all silo outputs into underwriter submission."""
    sections = {
        "executive_summary": {
            "deal_name": deal.get("project_name", ""),
            "sponsor": deal.get("sponsor_name", ""),
            "total_project_cost": deal.get("total_project_cost_usd", 0),
            "indicative_rating": maxwell_output.get("indicative_rating", ""),
            "recommended_structure": architect_output.get("recommendation", ""),
            "risk_level": sentinel_output.get("risk_level", ""),
        },
        "credit_analysis": maxwell_output,
        "structure_options": architect_output.get("candidates", []),
        "risk_assessment": sentinel_output,
        "pricing_analytics": pricing_output or {},
        "insurance_recommendation": insurance_output or {},
        "comparable_transactions": deal.get("comparables", []),
        "legal_opinions_index": deal.get("legal_opinions", []),
    }

    completeness = sum(1 for v in sections.values() if v)
    total = len(sections)

    return {
        "deal_id": deal.get("id", ""),
        "format": "ziegler_standard",
        "sections": sections,
        "completeness_pct": round(completeness / total * 100),
        "ready_for_submission": completeness == total,
        "generated_at": datetime.utcnow().isoformat(),
    }
