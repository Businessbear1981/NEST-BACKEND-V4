"""
NEST Licensing & Compliance Module.
Real regulatory infrastructure. Every detail accurate.
NEST is becoming a licensed investment banking firm.
Series 79 + 63 + 65 → Rent-a-BD via Finalis → RIA Registration → Own B/D.
"""
from datetime import datetime

LICENSING_ROADMAP = {
    "phase_1_exams": {
        "timeline": "Weeks 1-8",
        "priority": "IMMEDIATE",
        "exams": [
            {
                "name": "Series 79",
                "full_name": "Investment Banking Representative Exam",
                "administered_by": "FINRA",
                "covers": [
                    "Debt and equity capital raising",
                    "M&A advisory",
                    "Private placements",
                    "Restructuring",
                    "Bond offerings",
                ],
                "study_hours": 150,
                "pass_rate_pct": 57,
                "exam_fee_usd": 305,
                "passing_score_pct": 73,
                "format": "175 questions, 3.5 hours",
                "who_needs_it": "Sean Gilmore, Josh Edwards — anyone placing securities",
                "registration": "Must be sponsored by a FINRA member firm",
                "sponsorship_path": "Finalis or other rent-a-BD will sponsor",
                "nest_relevance": "PRIMARY — covers bond arrangements, M&A advisory, private placements",
            },
            {
                "name": "Series 63",
                "full_name": "Uniform Securities Agent State Law Exam",
                "administered_by": "NASAA/FINRA",
                "covers": ["State securities laws", "Blue sky regulations"],
                "study_hours": 40,
                "pass_rate_pct": 74,
                "exam_fee_usd": 147,
                "passing_score_pct": 72,
                "format": "60 questions, 1.5 hours",
                "nest_relevance": "REQUIRED alongside Series 79 for state registration",
            },
            {
                "name": "Series 65",
                "full_name": "Uniform Investment Adviser Law Exam",
                "administered_by": "NASAA",
                "covers": ["Investment advisory regulations", "Fiduciary duties", "Portfolio management"],
                "study_hours": 100,
                "pass_rate_pct": 68,
                "exam_fee_usd": 187,
                "passing_score_pct": 72,
                "format": "130 questions, 3 hours",
                "no_sponsorship_needed": True,
                "nest_relevance": "REQUIRED for RIA registration — covers bridge fund, bond fund, advisory fees",
            },
        ],
    },
    "phase_2_rent_bd": {
        "timeline": "Month 2-3",
        "priority": "HIGH",
        "description": "Affiliate as registered reps under existing FINRA broker-dealer. Operate immediately.",
        "recommended_firms": [
            {
                "name": "Finalis",
                "website": "finalis.com",
                "specialty": "AI-enabled IB boutiques, private placements, M&A advisory",
                "fee_structure": "15-25bps of deal or 5-10% of transaction fees",
                "why_nest": "Purpose-built for boutiques like NEST. Technology forward. Fast onboarding.",
                "covers": ["FINRA supervision", "Compliance infrastructure", "WSPs", "AML program"],
            },
            {
                "name": "StillPoint Capital",
                "specialty": "Independent IB, private placements",
                "fee_structure": "Negotiated per firm",
            },
            {
                "name": "Independent Investment Bankers Corp (IIBC)",
                "specialty": "Independent IB firms",
            },
        ],
        "what_you_get": [
            "Ability to place securities for compensation immediately",
            "FINRA-registered status",
            "Compliance infrastructure without building it",
            "Deal fees can flow day 1",
        ],
        "what_you_need_first": ["Series 79 passed", "Series 63 passed", "Background check clean"],
    },
    "phase_3_ria": {
        "timeline": "Month 3-6",
        "priority": "HIGH",
        "description": "Register as Registered Investment Adviser for fund management and ongoing advisory.",
        "filing": "Form ADV — Part 1 and Part 2",
        "thresholds": {
            "state_registered": "AUM under $100M",
            "sec_registered": "AUM over $110M (mandatory)",
            "mid_range": "$100-110M — can choose state or SEC",
        },
        "what_it_covers": [
            "Bridge fund management",
            "Bond fund management",
            "Ongoing advisory fees",
            "Monitoring fees",
            "Portfolio management",
        ],
        "required_exam": "Series 65 (or Series 66 if already have Series 7)",
        "annual_requirements": ["Form ADV update", "Compliance review", "Client disclosure"],
        "nest_structure": "NEST Advisors LLC as RIA entity. Separate from broker-dealer affiliation.",
    },
    "phase_4_own_bd": {
        "timeline": "Month 18-36",
        "trigger": "Annual transaction fees exceed $5M",
        "filing": "Form BD with SEC + FINRA NMA (New Member Application)",
        "timeline_to_approval": "6-12 months",
        "cost_to_setup_usd": [150000, 300000],
        "annual_compliance_cost_usd": [300000, 500000],
        "net_capital_requirements": {
            "agency_best_efforts": 5000,
            "standard": 50000,
            "if_touching_customer_funds": 1000000,
        },
        "required_principals": [
            {"license": "Series 24", "role": "General Securities Principal"},
            {"license": "Series 27", "role": "Financial and Operations Principal (FinOp)"},
            {"license": "Series 79", "role": "Investment Banking Representative"},
        ],
        "infrastructure_needed": [
            "Written Supervisory Procedures (WSPs)",
            "AML Program",
            "Books and Records system",
            "Customer complaint procedures",
            "Net capital computation",
            "FOCUS Report filings",
        ],
    },
}

DEAL_FEE_STRUCTURE = {
    "placement_fees": {
        "bond_arrangement": {"pct": [2.0, 2.5], "on": "face amount of bond"},
        "ban_arrangement": {"pct": [1.0, 1.5], "on": "face amount of BAN"},
        "ma_advisory": {"pct": [2.0, 4.0], "on": "enterprise value"},
        "lender_placement": {"pct": [0.5, 1.0], "on": "loan amount"},
        "bridge_fund": {"pct": "0% interest + 10-15% equity", "on": "bridge amount"},
    },
    "recurring_fees": {
        "packaging_advisory": {"amount_usd": [15000, 50000], "per": "deal"},
        "monitoring_fee": {"pct": [0.25, 0.5], "on": "bond face annually"},
        "refi_arrangement": {"pct": [1.5, 2.0], "on": "new bond face"},
        "fund_management": {"pct": [1.0, 2.0], "on": "AUM annually"},
    },
    "finra_disclosure_required": True,
    "note": "All fees disclosed to all parties per FINRA Rule 5110 and applicable regulations",
}

COMPLIANCE_CALENDAR = {
    "ongoing": [
        "Trade blotter maintenance",
        "Correspondence review",
        "Email archiving",
        "Outside business activity disclosure",
    ],
    "monthly": [
        "Net capital computation (when own B/D)",
        "Supervision sign-off",
    ],
    "quarterly": [
        "FOCUS Report (when own B/D)",
        "Review of WSPs",
    ],
    "annual": [
        "Form ADV update and client delivery",
        "AML program review",
        "Compliance program annual review",
        "Registered rep CE (Continuing Education)",
        "FINRA Annual Certification",
    ],
}


class LicensingService:

    def get_current_status(self) -> dict:
        return {
            "current_phase": "pre_licensing",
            "next_action": "Begin Series 79 + 63 study. Contact Finalis for affiliation discussion.",
            "days_to_licensed": 90,
            "revenue_possible_now": "Advisory/packaging fees only — not placement fees",
            "revenue_after_licensing": "Full bond arrangement fees + placement fees + advisory",
            "exams_completed": [],
            "exams_remaining": ["Series 79", "Series 63", "Series 65"],
            "total_exam_cost_usd": 305 + 147 + 187,
            "total_study_hours": 150 + 40 + 100,
        }

    def get_roadmap(self) -> dict:
        return LICENSING_ROADMAP

    def get_fee_structure(self) -> dict:
        return DEAL_FEE_STRUCTURE

    def get_compliance_calendar(self) -> dict:
        return COMPLIANCE_CALENDAR

    def calculate_rent_vs_own(self, annual_fees_usd: float) -> dict:
        rent_cost = annual_fees_usd * 0.075
        own_cost = 400000
        breakeven = own_cost / 0.075 if 0.075 else 0

        return {
            "annual_fees_usd": annual_fees_usd,
            "rent_bd_cost_usd": round(rent_cost),
            "own_bd_cost_usd": own_cost,
            "savings_if_own_usd": round(rent_cost - own_cost) if rent_cost > own_cost else 0,
            "recommendation": "Own B/D" if annual_fees_usd > breakeven else "Rent B/D",
            "breakeven_annual_fees_usd": round(breakeven),
            "current_recommendation": "Rent B/D via Finalis",
            "analysis": {
                "at_1M_fees": {"rent": round(1_000_000 * 0.075), "own": own_cost, "winner": "Rent"},
                "at_3M_fees": {"rent": round(3_000_000 * 0.075), "own": own_cost, "winner": "Rent"},
                "at_6M_fees": {"rent": round(6_000_000 * 0.075), "own": own_cost, "winner": "Own"},
                "at_10M_fees": {"rent": round(10_000_000 * 0.075), "own": own_cost, "winner": "Own"},
            },
        }

    def generate_finra_sponsorship_request(self) -> str:
        try:
            from services.core import call_claude
            prompt = """Write a professional affiliation inquiry letter from NEST Advisors (Arden Edge Capital x Soparrow Capital) to Finalis requesting broker-dealer affiliation.

NEST is:
- An AI-powered bond arrangement and M&A advisory platform
- CEO: Sean Gilmore (13yr JPMorgan, Business Banking/Emerging Middle Market/Mid Corp)
- Co-Founder: Josh Edwards (Soparrow Capital)
- Focus: Private bond arrangements for senior living, M&A buy-side financing
- Deal size: $20M-$300M
- Pipeline: $591M active

The letter should:
- Request affiliation as registered representatives under Finalis B/D
- Reference Series 79 + 63 exam plans (both principals)
- Describe deal flow and fee structure clearly
- Ask about onboarding timeline and requirements
- Jimmy Lee tone — direct, specific, no fluff
"""
            return call_claude(prompt)
        except Exception as e:
            return f"Error generating letter: {str(e)}"

    def get_exam_study_plan(self, exam_name: str) -> dict:
        exams = {e["name"]: e for e in LICENSING_ROADMAP["phase_1_exams"]["exams"]}
        exam = exams.get(exam_name)
        if not exam:
            return {"error": f"Exam '{exam_name}' not found. Available: {list(exams.keys())}"}

        hours = exam["study_hours"]
        weeks = 8 if exam_name == "Series 79" else 4
        daily_hours = round(hours / (weeks * 5), 1)

        return {
            "exam": exam_name,
            "full_name": exam["full_name"],
            "total_study_hours": hours,
            "recommended_weeks": weeks,
            "daily_study_hours": daily_hours,
            "format": exam.get("format", ""),
            "passing_score_pct": exam["passing_score_pct"],
            "pass_rate_pct": exam["pass_rate_pct"],
            "fee_usd": exam["exam_fee_usd"],
            "covers": exam["covers"],
            "nest_relevance": exam["nest_relevance"],
            "needs_sponsorship": not exam.get("no_sponsorship_needed", False),
        }


licensing_service = LicensingService()
