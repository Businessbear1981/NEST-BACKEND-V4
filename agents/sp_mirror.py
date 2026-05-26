"""
S&P Methodology Mirror Agent — Parallel to Moody's Mirror.

Applies S&P Global Ratings methodology: Business Risk Profile + Financial Risk Profile
→ Anchor → Modifiers → Rating.

Rating Scale: AAA, AA+, AA, AA-, A+, A, A-, BBB+, BBB, BBB-, BB+, BB, BB-, B+, B, B-
"""
from agents._claude import complete

SP_RATING_SCALE = [
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
    "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C", "D",
]

# S&P Business Risk Profile assessment (1=Excellent, 6=Vulnerable)
BUSINESS_RISK_CRITERIA = {
    "industry_risk": {
        "low": 1, "low_moderate": 2, "moderate": 3,
        "moderate_high": 4, "high": 5, "very_high": 6,
    },
    "competitive_position": {
        "excellent": 1, "strong": 2, "satisfactory": 3,
        "fair": 4, "weak": 5, "vulnerable": 6,
    },
}

# S&P Financial Risk Profile assessment (1=Minimal, 6=Highly Leveraged)
FINANCIAL_RISK_CRITERIA = {
    "minimal": 1, "modest": 2, "intermediate": 3,
    "significant": 4, "aggressive": 5, "highly_leveraged": 6,
}

# S&P Anchor Matrix: Business Risk (row) × Financial Risk (col) → base rating
ANCHOR_MATRIX = {
    (1, 1): "AAA", (1, 2): "AA+", (1, 3): "AA", (1, 4): "A+", (1, 5): "BBB+", (1, 6): "BB+",
    (2, 1): "AA+", (2, 2): "AA", (2, 3): "A+", (2, 4): "A-", (2, 5): "BBB", (2, 6): "BB",
    (3, 1): "AA", (3, 2): "A+", (3, 3): "A-", (3, 4): "BBB", (3, 5): "BB+", (3, 6): "BB-",
    (4, 1): "A+", (4, 2): "A-", (4, 3): "BBB", (4, 4): "BBB-", (4, 5): "BB", (4, 6): "B+",
    (5, 1): "A-", (5, 2): "BBB", (5, 3): "BB+", (5, 4): "BB", (5, 5): "BB-", (5, 6): "B",
    (6, 1): "BBB", (6, 2): "BB+", (6, 3): "BB", (6, 4): "BB-", (6, 5): "B+", (6, 6): "B-",
}

# Financial Risk thresholds by key metric
LEVERAGE_TO_FINANCIAL_RISK = [
    (1.5, "minimal"), (2.5, "modest"), (3.5, "intermediate"),
    (4.5, "significant"), (5.5, "aggressive"), (99, "highly_leveraged"),
]

SP_SYSTEM_PROMPT = """You are an S&P Global Ratings analyst simulator for NEST Advisors. You apply S&P's published rating methodology framework: Business Risk Profile + Financial Risk Profile → Anchor → Modifiers → Rating.

Given the anchor rating and modifier assessments, provide:
1. Your predicted S&P rating (use exact scale: AAA, AA+, AA, AA-, A+, A, A-, BBB+, BBB, BBB-, BB+, BB, BB-, B+, B, B-)
2. Business Risk Profile assessment rationale
3. Financial Risk Profile assessment rationale
4. Modifier impacts (diversification, capital structure, financial policy, liquidity, management/governance)
5. Comparable rating analysis — how similar credits in this sector are rated
6. Key differentiators from Moody's methodology for this deal

Be specific, direct, and analytical. No hedging. Speak as a senior S&P analyst would."""


class SPMirrorAgent:
    """Applies S&P Global Ratings methodology to predict bond ratings."""

    def __init__(self):
        self.name = "S&P Mirror Agent"
        self.desk = "rating"

    def predict_rating(self, deal: dict) -> dict:
        """Full S&P rating prediction."""
        brp = self.business_risk_profile(deal)
        frp = self.financial_risk_profile(deal)

        # Anchor from matrix
        biz_score = brp["composite_score"]
        fin_score = frp["composite_score"]
        anchor = ANCHOR_MATRIX.get((biz_score, fin_score), "BBB")

        # Modifiers
        modifiers = self._apply_modifiers(deal, anchor)
        final_rating = modifiers["adjusted_rating"]

        # AI narrative
        prompt = f"""Rate this deal using S&P methodology:

Sector: {deal.get('sector', 'corporate')}
DSCR: {deal.get('dscr', 0):.2f}x
Leverage: {deal.get('leverage', 0):.1f}x
Revenue: ${deal.get('revenue', 0):,.0f}
EBITDA: ${deal.get('ebitda', 0):,.0f}
Equity: {deal.get('equity_pct', 0):.0%}
Enhancement: {deal.get('enhancement', 'none')}

Business Risk Profile: {brp['assessment']} (score {biz_score})
  - Industry Risk: {brp['industry_risk']['assessment']}
  - Competitive Position: {brp['competitive_position']['assessment']}

Financial Risk Profile: {frp['assessment']} (score {fin_score})

Anchor Rating: {anchor}
Modifier adjustments: {modifiers['adjustments']}
Final Predicted Rating: {final_rating}"""

        narrative = complete(SP_SYSTEM_PROMPT, prompt, max_tokens=2048)

        return {
            "agency": "sp",
            "predicted_rating": final_rating,
            "anchor": anchor,
            "business_risk": brp,
            "financial_risk": frp,
            "modifiers": modifiers,
            "narrative": narrative,
        }

    def business_risk_profile(self, deal: dict) -> dict:
        """Assess S&P Business Risk Profile."""
        # Industry risk from sector
        sector_industry_risk = {
            "senior_living": "moderate", "hospitals": "moderate",
            "charter_schools": "moderate_high", "affordable_multifamily": "low_moderate",
            "corporate": "moderate", "software_saas": "low_moderate",
            "industrial_manufacturing": "moderate", "energy_services": "high",
            "data_centers": "low_moderate", "hospitality": "moderate_high",
        }
        industry = deal.get("industry_risk", sector_industry_risk.get(deal.get("sector", "corporate"), "moderate"))
        industry_score = BUSINESS_RISK_CRITERIA["industry_risk"].get(industry, 3)

        # Competitive position
        comp_pos = deal.get("competitive_position", "satisfactory")
        comp_score = BUSINESS_RISK_CRITERIA["competitive_position"].get(comp_pos, 3)

        # Composite business risk (average, rounded)
        composite = round((industry_score + comp_score) / 2)
        composite = max(1, min(composite, 6))

        assessment_map = {1: "Excellent", 2: "Strong", 3: "Satisfactory", 4: "Fair", 5: "Weak", 6: "Vulnerable"}

        return {
            "industry_risk": {"assessment": industry, "score": industry_score},
            "competitive_position": {"assessment": comp_pos, "score": comp_score},
            "composite_score": composite,
            "assessment": assessment_map.get(composite, "Satisfactory"),
        }

    def financial_risk_profile(self, deal: dict) -> dict:
        """Assess S&P Financial Risk Profile."""
        leverage = deal.get("leverage", 5.0)

        # Map leverage to financial risk category
        fin_risk = "intermediate"
        for threshold, category in LEVERAGE_TO_FINANCIAL_RISK:
            if leverage <= threshold:
                fin_risk = category
                break

        score = FINANCIAL_RISK_CRITERIA.get(fin_risk, 3)

        # DSCR adjustment
        dscr = deal.get("dscr", 1.0)
        if dscr >= 2.5:
            score = max(1, score - 1)
        elif dscr < 1.2:
            score = min(6, score + 1)

        return {
            "leverage": leverage,
            "dscr": dscr,
            "category": fin_risk,
            "composite_score": score,
            "assessment": fin_risk.replace("_", " ").title(),
        }

    def _apply_modifiers(self, deal: dict, anchor: str) -> dict:
        """Apply S&P modifiers to the anchor rating."""
        anchor_idx = SP_RATING_SCALE.index(anchor) if anchor in SP_RATING_SCALE else 9
        adjustments = []
        total_adj = 0

        # Diversification
        diversity = deal.get("revenue_diversity", "moderate")
        if diversity in ("excellent", "strong"):
            total_adj -= 1
            adjustments.append({"modifier": "diversification", "impact": -1, "reason": f"Strong revenue diversity ({diversity})"})
        elif diversity in ("weak", "poor"):
            total_adj += 1
            adjustments.append({"modifier": "diversification", "impact": +1, "reason": f"Weak revenue diversity ({diversity})"})

        # Liquidity
        days_cash = deal.get("days_cash_on_hand", 90)
        if days_cash >= 200:
            total_adj -= 1
            adjustments.append({"modifier": "liquidity", "impact": -1, "reason": f"Strong liquidity ({days_cash} days cash)"})
        elif days_cash < 60:
            total_adj += 1
            adjustments.append({"modifier": "liquidity", "impact": +1, "reason": f"Weak liquidity ({days_cash} days cash)"})

        # Management/governance
        mgmt = deal.get("management_quality", "adequate")
        if mgmt in ("excellent", "strong"):
            total_adj -= 1
            adjustments.append({"modifier": "management", "impact": -1, "reason": f"Strong management ({mgmt})"})

        # Enhancement override
        enhancement = deal.get("enhancement", "none")
        if enhancement == "bond_insurance":
            final_idx = SP_RATING_SCALE.index("AA") if "AA" in SP_RATING_SCALE else 2
            adjusted = SP_RATING_SCALE[final_idx]
            return {"anchor": anchor, "adjustments": adjustments + [{"modifier": "bond_insurance", "impact": "override to AA"}], "adjusted_rating": adjusted}
        elif enhancement in ("cash_collateralized_lc", "federal_guarantee"):
            return {"anchor": anchor, "adjustments": adjustments + [{"modifier": enhancement, "impact": "override to AAA"}], "adjusted_rating": "AAA"}

        # Apply adjustments
        final_idx = max(0, min(anchor_idx + total_adj, len(SP_RATING_SCALE) - 1))
        adjusted = SP_RATING_SCALE[final_idx]

        return {"anchor": anchor, "adjustments": adjustments, "total_notch_adjustment": total_adj, "adjusted_rating": adjusted}

    def identify_levers(self, deal: dict, assessment: dict = None) -> list[dict]:
        """Identify structural levers from S&P perspective."""
        levers = []
        enhancement = deal.get("enhancement", "none")

        if enhancement == "none":
            levers.append({"lever": "Bond insurance", "sp_impact": "Override to AA", "cost_range": "15-40 bps"})
            levers.append({"lever": "Cash-collateralized LC", "sp_impact": "Override to AAA", "cost_range": "Sponsor cash deployment"})

        if deal.get("leverage", 5) > 4.0:
            levers.append({"lever": "Reduce leverage below 4.0x", "sp_impact": "Financial Risk improves 1 category", "mechanism": "Larger equity check or smaller bond"})

        if deal.get("revenue_diversity", "moderate") in ("weak", "poor"):
            levers.append({"lever": "Demonstrate revenue diversity", "sp_impact": "Diversification modifier -1 notch", "mechanism": "Show contracted revenue, geographic spread"})

        return levers
