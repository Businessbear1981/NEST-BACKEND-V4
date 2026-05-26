"""
NEST Audit Package Generator — Silo 9
TPMG / Moss Adams ready financials.
Formats Atlas/Modeling outputs into audit working papers.
"""
from datetime import datetime


def generate_package(deal: dict, modeling_outputs: dict,
                     maxwell_output: dict = None) -> dict:
    """Generate audit-ready package from upstream silo outputs."""
    sections = []

    # Balance Sheet
    sections.append({
        "section": "Balance Sheet",
        "type": "financial_statement",
        "data": {
            "total_assets": deal.get("total_assets_usd", 0),
            "total_liabilities": deal.get("total_debt", 0),
            "net_worth": deal.get("total_assets_usd", 0) - deal.get("total_debt", 0),
        },
        "footnotes": ["Assets stated at appraised value per independent appraisal"],
        "status": "draft",
    })

    # Income Statement
    noi_data = modeling_outputs.get("noi", {})
    sections.append({
        "section": "Income Statement",
        "type": "financial_statement",
        "data": noi_data,
        "footnotes": ["Revenue recognition per ASC 606"],
        "status": "draft",
    })

    # Cash Flow Statement
    sections.append({
        "section": "Statement of Cash Flows",
        "type": "financial_statement",
        "data": modeling_outputs.get("ccsr", {}),
        "footnotes": ["Cash basis presentation — see Note 3 for GAAP reconciliation"],
        "status": "draft",
    })

    # Debt Schedule
    sections.append({
        "section": "Debt Schedule",
        "type": "supporting_schedule",
        "data": {
            "a_tranche": deal.get("a_tranche_usd", 0),
            "b_tranche": deal.get("b_tranche_usd", 0),
            "total_debt": deal.get("a_tranche_usd", 0) + deal.get("b_tranche_usd", 0),
            "a_coupon": deal.get("a_coupon_pct", 7.0),
            "b_coupon": deal.get("b_coupon_pct", 11.0),
        },
        "status": "draft",
    })

    # Internal Controls
    sections.append({
        "section": "Internal Controls Documentation",
        "type": "controls",
        "data": {
            "segregation_of_duties": deal.get("sod_documented", False),
            "bank_reconciliation": deal.get("bank_recon", False),
            "approval_matrix": deal.get("approval_matrix", False),
        },
        "status": "pending_review",
    })

    completed = sum(1 for s in sections if s["status"] == "final")
    return {
        "deal_id": deal.get("id", ""),
        "target_auditor": deal.get("auditor", "TPMG"),
        "sections": sections,
        "total_sections": len(sections),
        "completed_sections": completed,
        "completion_pct": round(completed / len(sections) * 100),
        "package_status": "ready" if completed == len(sections) else "in_progress",
        "generated_at": datetime.utcnow().isoformat(),
    }
