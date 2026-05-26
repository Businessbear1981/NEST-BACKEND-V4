"""
Moody's Methodology Mirror Agent — NEST's signature capability.

Applies Moody's published methodology frameworks to predict bond ratings
before formal agency engagement. Scorecard-based quantitative assessment
plus Claude AI narrative opinion.

Rating Scale: Aaa, Aa1-Aa3, A1-A3, Baa1-Baa3, Ba1-Ba3, B1-B3, Caa1-Caa3, Ca, C
"""
from agents._claude import complete

MOODYS_RATING_SCALE = [
    "Aaa", "Aa1", "Aa2", "Aa3", "A1", "A2", "A3",
    "Baa1", "Baa2", "Baa3", "Ba1", "Ba2", "Ba3",
    "B1", "B2", "B3", "Caa1", "Caa2", "Caa3", "Ca", "C",
]

# Sector-specific weight calibrations
SECTOR_WEIGHTS = {
    "senior_living": {"quantitative": 0.55, "qualitative": 0.45, "key_metric": "dscr", "occupancy_weight": 0.15},
    "hospitals": {"quantitative": 0.55, "qualitative": 0.45, "key_metric": "dscr", "days_cash_weight": 0.12},
    "charter_schools": {"quantitative": 0.50, "qualitative": 0.50, "key_metric": "dscr", "enrollment_weight": 0.15},
    "affordable_multifamily": {"quantitative": 0.60, "qualitative": 0.40, "key_metric": "dscr"},
    "corporate": {"quantitative": 0.60, "qualitative": 0.40, "key_metric": "leverage"},
    "default": {"quantitative": 0.60, "qualitative": 0.40, "key_metric": "dscr"},
}

# Quantitative factor scoring (1=Aaa, 2=Aa, 3=A, 4=Baa, 5=Ba, 6=B)
DSCR_SCORES = [
    (3.0, 1), (2.5, 2), (2.0, 3), (1.5, 4), (1.2, 5), (1.0, 6), (0, 7),
]
LEVERAGE_SCORES = [
    (1.5, 1), (2.5, 2), (3.5, 3), (4.5, 4), (5.5, 5), (6.5, 6), (99, 7),
]
LIQUIDITY_SCORES = [
    (300, 1), (200, 2), (150, 3), (90, 4), (60, 5), (30, 6), (0, 7),
]

# Structural notching adjustments
STRUCTURAL_ADJUSTMENTS = {
    "dsrf_mads": -0.5,         # DSRF at MADS → lift ~0.5 notch
    "dsrf_none": +1.0,        # No DSRF → weaken 1 notch
    "bond_insurance": -3.0,    # Bond insurance lifts to insurer rating (AA)
    "loc_investment_grade": -3.0,  # IG LOC → lift to LC bank rating
    "cash_collateralized_lc": -5.0,  # Cash-collateralized → near-Aaa
    "federal_guarantee": -6.0,  # FHA/USDA/GNMA → Aaa-equivalent
    "strong_covenants": -0.5,  # Restrictive covenants (1.20x vs 1.10x) → lift
    "weak_covenants": +0.5,    # Permissive covenants → weaken
    "high_equity": -0.5,      # 30%+ equity → lift
    "low_equity": +0.5,       # <20% equity → weaken
}

MOODYS_SYSTEM_PROMPT = """You are a Moody's Investors Service rating analyst simulator for NEST Advisors. You apply Moody's published rating methodology to produce a rating opinion.

Given a scorecard with quantitative and qualitative factors already scored, provide:
1. Your predicted Moody's rating (use the exact scale: Aaa, Aa1-Aa3, A1-A3, Baa1-Baa3, Ba1-Ba3, B1-B3)
2. Key strengths supporting the rating
3. Key risks that constrain the rating
4. Structural levers that could move the rating up or down
5. Comparison to typical ratings in this sector

Be specific, direct, and analytical. No hedging. Speak as a senior Moody's analyst would to a credit committee."""


class MoodysMirrorAgent:
    """Applies Moody's methodology to predict bond ratings."""

    def __init__(self):
        self.name = "Moody's Mirror Agent"
        self.desk = "rating"

    def predict_rating(self, deal: dict) -> dict:
        """Full rating prediction with scorecard + AI narrative."""
        scorecard = self.scorecard(deal)
        levers = self.identify_levers(deal, scorecard)

        # AI narrative opinion
        prompt = f"""Rate this deal using Moody's methodology:

Sector: {deal.get('sector', 'corporate')}
DSCR: {deal.get('dscr', 0):.2f}x
Leverage: {deal.get('leverage', 0):.1f}x
Revenue: ${deal.get('revenue', 0):,.0f}
EBITDA: ${deal.get('ebitda', 0):,.0f}
Equity contribution: {deal.get('equity_pct', 0):.0%}
Enhancement: {deal.get('enhancement', 'none')}
Sponsor experience: {deal.get('sponsor_experience_years', 0)} years
Management quality: {deal.get('management_quality', 'adequate')}
Market position: {deal.get('market_position', 'moderate')}
Revenue diversity: {deal.get('revenue_diversity', 'moderate')}

Scorecard composite: {scorecard['composite_score']:.1f} (1=Aaa, 7=C)
Predicted rating from scorecard: {scorecard['predicted_rating']}

Structural adjustments applied: {scorecard.get('adjustments_applied', [])}"""

        narrative = complete(MOODYS_SYSTEM_PROMPT, prompt, max_tokens=2048)

        return {
            "agency": "moodys",
            "predicted_rating": scorecard["predicted_rating"],
            "scorecard": scorecard,
            "structural_levers": levers,
            "narrative": narrative,
        }

    def scorecard(self, deal: dict) -> dict:
        """Score deal on Moody's quantitative + qualitative factors."""
        sector = deal.get("sector", "default")
        weights = SECTOR_WEIGHTS.get(sector, SECTOR_WEIGHTS["default"])

        # Quantitative factors
        dscr = deal.get("dscr", 1.0)
        leverage = deal.get("leverage", 5.0)
        days_cash = deal.get("days_cash_on_hand", 90)

        dscr_score = next((s for threshold, s in DSCR_SCORES if dscr >= threshold), 7)
        leverage_score = next((s for threshold, s in LEVERAGE_SCORES if leverage <= threshold), 7)
        liquidity_score = next((s for threshold, s in LIQUIDITY_SCORES if days_cash >= threshold), 7)

        quant_score = (dscr_score * 0.40 + leverage_score * 0.35 + liquidity_score * 0.25)

        # Qualitative factors
        quality_map = {"excellent": 1, "strong": 2, "good": 3, "adequate": 4, "weak": 5, "poor": 6}
        mgmt_score = quality_map.get(deal.get("management_quality", "adequate"), 4)
        market_score = quality_map.get(deal.get("market_position", "moderate"), 4)
        diversity_score = quality_map.get(deal.get("revenue_diversity", "moderate"), 4)
        governance_score = quality_map.get(deal.get("governance", "adequate"), 4)

        qual_score = (mgmt_score * 0.30 + market_score * 0.30 + diversity_score * 0.25 + governance_score * 0.15)

        # Composite
        composite = quant_score * weights["quantitative"] + qual_score * weights["qualitative"]

        # Structural adjustments
        adjustments = []
        enhancement = deal.get("enhancement", "none")
        if enhancement in STRUCTURAL_ADJUSTMENTS:
            adj = STRUCTURAL_ADJUSTMENTS[enhancement]
            composite += adj
            adjustments.append({"factor": enhancement, "adjustment": adj})

        if deal.get("dsrf_type") == "mads":
            composite += STRUCTURAL_ADJUSTMENTS["dsrf_mads"]
            adjustments.append({"factor": "dsrf_mads", "adjustment": STRUCTURAL_ADJUSTMENTS["dsrf_mads"]})

        equity_pct = deal.get("equity_pct", 0.20)
        if equity_pct >= 0.30:
            composite += STRUCTURAL_ADJUSTMENTS["high_equity"]
            adjustments.append({"factor": "high_equity", "adjustment": STRUCTURAL_ADJUSTMENTS["high_equity"]})
        elif equity_pct < 0.20:
            composite += STRUCTURAL_ADJUSTMENTS["low_equity"]
            adjustments.append({"factor": "low_equity", "adjustment": STRUCTURAL_ADJUSTMENTS["low_equity"]})

        # Map composite to rating
        composite = max(1, min(composite, 7))
        rating_idx = min(int((composite - 1) * 3), len(MOODYS_RATING_SCALE) - 1)
        predicted = MOODYS_RATING_SCALE[max(0, rating_idx)]

        return {
            "quantitative": {
                "dscr": {"value": dscr, "score": dscr_score},
                "leverage": {"value": leverage, "score": leverage_score},
                "liquidity": {"value": days_cash, "score": liquidity_score},
                "composite": round(quant_score, 2),
                "weight": weights["quantitative"],
            },
            "qualitative": {
                "management": {"assessment": deal.get("management_quality", "adequate"), "score": mgmt_score},
                "market_position": {"assessment": deal.get("market_position", "moderate"), "score": market_score},
                "revenue_diversity": {"assessment": deal.get("revenue_diversity", "moderate"), "score": diversity_score},
                "governance": {"assessment": deal.get("governance", "adequate"), "score": governance_score},
                "composite": round(qual_score, 2),
                "weight": weights["qualitative"],
            },
            "composite_score": round(composite, 2),
            "predicted_rating": predicted,
            "adjustments_applied": adjustments,
            "sector": sector,
        }

    def identify_levers(self, deal: dict, scorecard: dict = None) -> list[dict]:
        """Identify structural levers that could improve the rating."""
        if not scorecard:
            scorecard = self.scorecard(deal)

        levers = []
        composite = scorecard["composite_score"]
        enhancement = deal.get("enhancement", "none")

        if enhancement == "none":
            levers.append({"lever": "Add bond insurance (BAM/Assured Guaranty)", "impact": "Lift to AA (insurer rating)", "notches": "+3-4", "cost": "15-40 bps annual premium"})
            levers.append({"lever": "Add LOC from investment-grade bank", "impact": "Lift to bank's short-term rating", "notches": "+3-4", "cost": "25-75 bps annual fee"})

        dscr = deal.get("dscr", 1.0)
        if dscr < 1.5:
            levers.append({"lever": "Increase DSCR to 1.50x+ through structure", "impact": "Potential 1 notch improvement", "notches": "+1", "mechanism": "Reduce bond size, extend amortization, or increase equity"})

        equity = deal.get("equity_pct", 0.20)
        if equity < 0.30:
            levers.append({"lever": "Increase sponsor equity to 30%+", "impact": "0.5 notch improvement", "notches": "+0.5", "mechanism": "Larger equity check reduces leverage"})

        covenant_dscr = deal.get("covenant_dscr", 1.10)
        if covenant_dscr < 1.20:
            levers.append({"lever": "Tighten DSCR covenant to 1.20x", "impact": "0.5 notch improvement", "notches": "+0.5", "mechanism": "Stronger covenant package demonstrates credit discipline"})

        if not deal.get("dsrf_type"):
            levers.append({"lever": "Fund DSRF at MADS", "impact": "0.5 notch improvement", "notches": "+0.5", "mechanism": "Debt service reserve provides cushion"})

        return levers
