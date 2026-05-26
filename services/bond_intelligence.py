"""
NEST Bond Intelligence
Institutional knowledge from reverse-engineering real bond transactions.
Capital Trust Authority BAN + Jacaranda Trace PLOM + 20yr JPMorgan experience.
Every rule here is from a real deal.
"""
from datetime import datetime
from typing import Optional

BOND_TYPES = {
    "BAN": {
        "name": "Bond Anticipation Note",
        "description": "Short-term bridge. Funds pre-development and land. Converts to revenue bond when milestones achieved. Zero coupon accreting structure typical.",
        "typical_term_years": [1, 5],
        "typical_rate_pct": [8, 15],
        "minimum_buyers": "QIBs and institutional accredited investors only",
        "security": ["senior_mortgage", "trust_estate", "project_fund"],
        "typical_size_usd": [5_000_000, 50_000_000],
        "converts_to": "revenue_bond",
        "conversion_triggers": ["presales_50pct", "feasibility_complete", "GMP_executed", "all_permits"],
        "real_example": "Capital Trust Authority Series 2024A — $23.4M — Convivial St. Pete — B.C. Ziegler",
        "nest_play": "Arrange the BAN. Monitor milestones. Arrange the long-term bond. Two arrangement fees, same client.",
        "nest_arrangement_fee_pct": 1.5,
    },
    "REVENUE_BOND": {
        "name": "Revenue Bond",
        "description": "Long-term permanent financing. Tax-exempt. Rated. Backed by project revenue (NOI, entrance fees, monthly service fees). Issued through conduit authority.",
        "typical_term_years": [25, 35],
        "typical_rate_pct": [5.5, 8.5],
        "rating_required": True,
        "minimum_dscr": 1.20,
        "debt_service_reserve": "6 months to 1 year maximum annual debt service",
        "security": ["revenue_pledge", "debt_service_reserve", "rate_covenant", "first_mortgage"],
        "typical_size_usd": [20_000_000, 500_000_000],
        "issuers": ["Capital Trust Authority", "LGFC", "Health Facilities Authority"],
        "real_example": "Jacaranda Trace PLOM Series 2025 — $231M — Florida LGFC",
        "nest_play": "Full bond arrangement. 2-2.5% fee. Hylant surety wrap. Perpetual equity warrant.",
        "nest_arrangement_fee_pct": 2.25,
    },
    "DUAL_TRANCHE_NEST": {
        "name": "NEST Dual-Tranche Private Bond",
        "description": "NEST proprietary. Series A (75% LTC, investment grade, Hylant surety) + Series B (7% addon, bank-managed HFT). 10-15 refi cycles. Perpetual equity.",
        "a_tranche_ltc_pct": 75,
        "b_tranche_addon_pct": 7,
        "a_coupon_pct": [6.5, 7.5],
        "b_coupon_pct": [10.0, 14.0],
        "surety": "Hylant Insurance — performance bond",
        "b_tranche_use": "bank HFT fund → 15-25% return → services B coupon → surplus = war chest",
        "refi_cycles": [10, 15],
        "nest_arrangement_fee_pct": 2.25,
        "equity_warrant_pct": [2.0, 5.0],
        "blueprint": "Jacaranda Trace PLOM, Series 2025, $231M, Florida LGFC",
        "nest_play": "Maximum NEST economics. Arrangement fee + refi fees + equity + placement. All four revenue streams.",
    },
}

GRADING_CRITERIA = {
    "A": {
        "description": "Top investment grade. Lowest coupon. Institutional market.",
        "minimum_dscr": 2.0,
        "maximum_ltv_pct": 55,
        "minimum_presales_pct": 80,
        "operator_years_min": 10,
        "requires_audit": True,
        "requires_rating": True,
        "debt_service_reserve": "1 year MADS",
        "coupon_range_pct": [5.5, 6.5],
        "what_it_takes": [
            "Experienced operator — 10+ years, multiple facilities",
            "DSCR 2.0x+ at stabilization",
            "LTV below 55%",
            "80%+ presales",
            "Big 4 or national CPA auditor",
            "S&P or Moody's rating",
            "Name-brand surety (Hylant, Travelers, Zurich)",
            "Strong primary market — MSA 500K+",
        ],
    },
    "BBB-": {
        "description": "Investment grade. NEST sweet spot. Jacaranda Trace territory.",
        "minimum_dscr": 1.5,
        "maximum_ltv_pct": 70,
        "minimum_presales_pct": 70,
        "operator_years_min": 5,
        "requires_audit": False,
        "requires_review": True,
        "debt_service_reserve": "6 months",
        "coupon_range_pct": [6.5, 7.5],
        "what_it_takes": [
            "Operator with 5+ year track record",
            "DSCR 1.5x at stabilization",
            "LTV below 70%",
            "70%+ presales at closing",
            "CPA-reviewed or audited financials",
            "GMP contract executed",
            "Credit enhancement (Hylant surety or LC)",
            "Independent feasibility study",
        ],
    },
    "BAN_UNRATED": {
        "description": "Speculative. Pre-development. QIB/accredited only. Like St. Pete Convivial.",
        "minimum_dscr": 0,
        "maximum_ltv_pct": 85,
        "minimum_presales_pct": 0,
        "requires_audit": False,
        "rating_required": False,
        "buyers": "QIBs and institutional accredited investors only",
        "coupon_range_pct": [10, 15],
        "structure": "zero coupon accreting, compounded semiannually",
        "what_it_takes": [
            "Land control (contract or purchased)",
            "Provisional COA from state insurance regulator",
            "Architect engaged — schematic plans",
            "Letter of intent from operator",
            "Market study (not full feasibility)",
            "Qualified institutional buyer market",
        ],
        "real_example": "Series 2024A — $23.4M — 12% accreting — matures Oct 2029",
    },
}

MILESTONE_GATES = [
    {"gate": 1, "name": "Site Control", "required_for": "BAN",
     "docs": ["PSA or deed", "title_commitment", "survey"],
     "nest_fee_opportunity": "Packaging fee $15-25K"},
    {"gate": 2, "name": "Entitlements", "required_for": "BAN",
     "docs": ["zoning_approval", "CUP_if_required"],
     "nest_fee_opportunity": "Consulting fee"},
    {"gate": 3, "name": "Provisional COA", "required_for": "BAN issuance",
     "docs": ["PCOA_letter", "OIR_application"],
     "note": "Florida: OIR issues PCOA. Allows marketing before full COA."},
    {"gate": 4, "name": "50% Presales", "presale_pct": 50,
     "required_for": "Full COA application",
     "docs": ["reservation_agreements", "deposit_receipts"],
     "nest_alert": "Alert at 40% — 50% gate approaching"},
    {"gate": 5, "name": "Financial Feasibility Complete",
     "required_for": "Long-term bond offering",
     "docs": ["feasibility_study", "market_study", "10yr_projections"],
     "timeline_weeks": [8, 16],
     "nest_automates": "Prometheus generates preliminary in 3 days"},
    {"gate": 6, "name": "GMP Contract Executed",
     "required_for": "Long-term bond",
     "docs": ["GMP_contract", "GC_license", "bonding_capacity", "construction_schedule"],
     "nest_alert": "Alert on any change order >5% of GMP"},
    {"gate": 7, "name": "70% Presales", "presale_pct": 70,
     "required_for": "Long-term bond closing",
     "docs": ["binding_reservation_agreements"],
     "nest_alert": "Alert at 60% — 70% gate approaching"},
    {"gate": 8, "name": "Financing Commitment",
     "required_for": "Full COA issuance",
     "docs": ["commitment_letter", "term_sheet"]},
    {"gate": 9, "name": "Long-Term Bond Closes — BAN Redeemed",
     "docs": ["bond_indenture", "closing_certificates", "legal_opinions"],
     "nest_fee": "2.25% of long-term bond face"},
    {"gate": 10, "name": "Stabilized + NEST Exit",
     "docs": ["certificate_of_occupancy", "stabilized_financials"],
     "nest_fee": "Warrant exercise or equity sale"},
]

PROFESSIONAL_TEAM = {
    "bond_counsel": {
        "role": "Issues tax-exempt opinion. Required for all municipal bonds.",
        "required": True,
        "typical_fee_pct": [0.10, 0.30],
        "florida_firms": ["Nabors, Giblin & Nickerson PA", "Bryant Miller Olive PA", "Greenberg Traurig"],
        "st_pete_example": "Nabors, Giblin & Nickerson PA — Tampa",
    },
    "underwriter": {
        "role": "Books and places bonds with investors.",
        "discount_pct": [0.5, 2.0],
        "senior_living_specialists": ["B.C. Ziegler and Company", "Piper Sandler", "Stifel", "Baird"],
        "st_pete_example": "B.C. Ziegler and Company",
        "nest_note": "B.C. Ziegler is the dominant senior living bond underwriter in the US.",
    },
    "trustee": {
        "role": "Administers trust estate. Receives payments. Distributes to holders.",
        "annual_fee_usd": [5000, 25000],
        "firms": ["UMB Bank NA", "US Bank", "Regions Bank", "Wilmington Trust"],
        "st_pete_example": "UMB Bank, N.A.",
    },
    "financial_feasibility": {
        "role": "Independent feasibility study. Required for rated bonds.",
        "firms": ["CliftonLarsonAllen LLP", "Ziegler Credit Corp", "Health Trust", "VMG Health"],
        "fee_usd": [30000, 80000],
        "timeline_weeks": [8, 16],
        "st_pete_example": "CliftonLarsonAllen LLP — Compilation Report July 2024",
        "nest_automates": "Prometheus generates preliminary feasibility in 3 days",
    },
    "appraiser": {
        "role": "Appraises land value and as-if-complete project value.",
        "firms": ["Health Trust", "Cushman Wakefield", "CBRE", "JLL"],
        "fee_usd": [10000, 25000],
        "timeline_weeks": [3, 6],
        "st_pete_example": "Health Trust — $11.7M as-is value Feb 2024",
    },
    "project_monitor": {
        "role": "Monthly construction oversight for bondholders.",
        "fee_monthly_usd": [2000, 5000],
        "duties": ["draw_review", "site_inspection", "budget_variance", "schedule_review"],
        "nest_automates": "NEST construction monitor agent does this automatically",
    },
}

REQUIRED_DOCUMENTS = {
    "BAN": {
        "financial": [
            "Compilation report (CPA)",
            "Pre-development budget",
            "Sources and uses of funds",
            "Market study (not full feasibility)",
        ],
        "legal": [
            "Trust indenture",
            "Loan agreement",
            "Bond purchase contract",
            "Senior mortgage",
            "Investor letter (Reg D)",
            "Entity formation documents",
        ],
        "regulatory": [
            "Provisional COA",
            "Phase I Environmental",
            "Zoning approvals",
        ],
        "technical": [
            "Appraisal (as-is)",
            "Title insurance",
            "Survey",
            "Architectural plans (schematic)",
        ],
    },
    "REVENUE_BOND": {
        "financial": [
            "Audited financial statements (3 years)",
            "Full financial feasibility study",
            "GMP construction contract",
            "Sources and uses of funds",
            "10-year pro forma",
            "Debt service schedule",
            "Working capital analysis",
            "Rate covenant analysis",
        ],
        "legal": [
            "Trust indenture",
            "Loan agreement",
            "Bond purchase contract",
            "First mortgage",
            "Collateral assignment",
            "Management agreement",
            "Development agreement",
            "Construction contract",
        ],
        "regulatory": [
            "Full COA (70% presales required)",
            "All building permits",
            "Phase I Environmental",
            "Zoning approvals",
            "Healthcare licensing if applicable",
        ],
        "technical": [
            "USPAP appraisal (as-is + as-if-complete)",
            "Market feasibility study",
            "Title insurance",
            "Survey",
            "Geotechnical report",
            "Full architectural/engineering plans",
        ],
    },
}

HUNDRED_PCT_FINANCING = {
    "description": "Developer controls project with zero equity. Pure bond financing.",
    "steps": [
        "BAN closes — funds land + pre-dev ($20-30M). Developer contributes no equity.",
        "Marketing begins — entrance fee deposits collected from presale reservations.",
        "50% presales → COA application eligible. Deposits held in escrow.",
        "GMP executed → construction ready to begin.",
        "70% presales → Long-term revenue bond closes ($150-300M). BAN redeemed.",
        "Entrance fee escrow funds IO payments during construction.",
        "Construction completes. Certificate of occupancy.",
        "Lease-up begins. Residents move in. Monthly fees start.",
        "At 90%+ occupancy: NOI covers 1.5x+ debt service from operations.",
        "Refinance: property value now 150%+ of debt. Developer captures equity.",
        "NEST warrant exercises. NEST receives 2-5% of enterprise value.",
    ],
    "key_formula": "Entrance fee per unit × 70% presold = construction period cash flow",
    "risk": "If presales miss 70% target, BAN may mature before long-term bond closes",
    "nest_play": "NEST earns on BAN arrangement + long-term bond arrangement + monitoring + warrant exit",
}


class BondIntelligence:

    def assess_rating_readiness(self, deal: dict) -> dict:
        dscr = deal.get("dscr_stabilized", 0)
        ltv = deal.get("ltv_pct", 100)
        presales = deal.get("presales_pct", 0)
        has_audit = deal.get("has_audited_financials", False)
        has_feasibility = deal.get("has_feasibility_study", False)
        has_GMP = deal.get("has_GMP_contract", False)
        op_years = deal.get("operator_years_experience", 0)

        achievable = []
        gaps = []

        if (dscr >= 2.0 and ltv <= 55 and presales >= 80
                and has_audit and has_feasibility and has_GMP and op_years >= 10):
            achievable.append("A")

        if (dscr >= 1.5 and ltv <= 70 and presales >= 70
                and has_feasibility and has_GMP and op_years >= 5):
            achievable.append("BBB-")

        achievable.append("BAN (unrated, QIB only)")

        if dscr < 1.5:
            gaps.append(f"DSCR {dscr:.2f}x below 1.5x BBB- minimum")
        if ltv > 70:
            gaps.append(f"LTV {ltv:.1f}% above 70% BBB- threshold")
        if presales < 70:
            gaps.append(f"Presales {presales:.0f}% — 70% needed for long-term bond")
        if not has_feasibility:
            gaps.append("Financial feasibility study required (8-16 weeks, $30-80K)")
        if not has_GMP:
            gaps.append("GMP contract with licensed GC required")
        if not has_audit and "BBB-" not in achievable:
            gaps.append("Reviewed or audited financials required")

        return {
            "achievable_ratings": achievable,
            "highest_achievable": achievable[0] if achievable else "Cannot proceed",
            "gaps": gaps,
            "next_action": gaps[0] if gaps else "Ready for bond structuring",
            "estimated_coupon": (
                GRADING_CRITERIA.get(achievable[0], {}).get("coupon_range_pct")
                if achievable and achievable[0] in GRADING_CRITERIA else [10, 15]
            ),
        }

    def get_document_checklist(self, bond_type: str = "REVENUE_BOND") -> dict:
        docs = REQUIRED_DOCUMENTS.get(bond_type, REQUIRED_DOCUMENTS["REVENUE_BOND"])
        total = sum(len(v) for v in docs.values())
        return {"bond_type": bond_type, "documents": docs,
                "total_items": total, "categories": list(docs.keys())}

    def get_milestone_status(self, current_gate: int,
                             presales_pct: float = 0,
                             has_feasibility: bool = False,
                             has_GMP: bool = False) -> dict:
        current = next((g for g in MILESTONE_GATES if g["gate"] == current_gate), MILESTONE_GATES[0])
        next_gate = next((g for g in MILESTONE_GATES if g["gate"] == current_gate + 1), None)
        return {
            "current_gate": current,
            "next_gate": next_gate,
            "pct_to_100_financing": round(current_gate / 10 * 100),
            "gates_remaining": 10 - current_gate,
            "refinance_ready": presales_pct >= 70 and has_feasibility and has_GMP,
        }

    def get_financing_path(self, stage: str, amount: float, presales: float) -> dict:
        if stage == "pre_development":
            return {"structure": "BAN", "achievable_usd": min(amount * 0.15, 30_000_000),
                    "timeline_weeks": 12, "nest_fee_usd": min(amount * 0.15, 30_000_000) * 0.015,
                    "next_milestone": "Obtain Provisional COA"}
        if stage == "50_pct_presold":
            return {"structure": "Begin long-term bond process",
                    "achievable_usd": amount * 0.82, "timeline_weeks": 24,
                    "nest_fee_usd": amount * 0.82 * 0.0225,
                    "next_milestone": "Complete feasibility study + GMP"}
        if stage == "70_pct_presold":
            return {"structure": "Revenue bond closing",
                    "achievable_usd": amount, "timeline_weeks": 20,
                    "nest_fee_usd": amount * 0.0225,
                    "next_milestone": "Close long-term bond — redeem BAN",
                    "hundred_pct_financing": True}
        return {"structure": "Assess project stage", "achievable_usd": 0}


bond_intel = BondIntelligence()
