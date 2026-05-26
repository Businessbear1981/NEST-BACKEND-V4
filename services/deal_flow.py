"""
NEST Deal Flow Orchestrator — wires desks together.

A deal enters at BD/intake and flows:
BD → Bond Desk (sizing) → Credit UW (memo + grade) → Rating (prediction)
→ Structuring (terms) → Enhancement (if needed) → Documents (package)
→ Placement (marketing) → Closing → Operations (admin) → Surveillance

Each transition carries specific data. This orchestrator manages
what data flows between desks and validates completeness.
"""
from __future__ import annotations
from datetime import datetime


class DealFlow:
    """Orchestrates deal lifecycle across desks."""

    def __init__(self):
        from services.intelligence_engine import IntelligenceEngine
        self.intel = IntelligenceEngine()

    def run_intake(self, deal: dict) -> dict:
        """Stage 1: BD intake → Bond Desk. Runs sizing, enriches deal."""
        sizing = self.intel.size_bond(deal)
        deal["bond_amount"] = sizing.get("capital_structure", {}).get("senior_bond", 0)
        deal["enterprise_value"] = sizing.get("valuation", {}).get("enterprise_value", 0)
        deal["dscr"] = sizing.get("credit", {}).get("dscr", 0)
        deal["credit_grade"] = sizing.get("credit", {}).get("grade", "")
        deal["leverage"] = sizing.get("capital_structure", {}).get("total_leverage", 0)
        deal["sources_and_uses"] = sizing.get("sources_and_uses", {})
        deal["readiness_flags"] = sizing.get("readiness_flags", [])
        deal["pricing"] = sizing.get("bond_structure", {})
        deal["reserves"] = sizing.get("reserves", {})
        deal["fees"] = sizing.get("fees", {})
        deal["stage"] = "intake_complete"
        deal.setdefault("desk_outputs", {})["bond_desk"] = sizing
        deal["stage_timestamp"] = datetime.utcnow().isoformat()
        return deal

    def run_credit(self, deal: dict) -> dict:
        """Stage 2: Credit Underwriting. Policy check + credit memo."""
        uw_result = self.intel.underwrite({
            "dscr": deal.get("dscr", 0),
            "total_leverage": deal.get("leverage", 0),
            "equity_pct": deal.get("equity_pct", 0),
            "sponsor_experience_years": deal.get("sponsor_experience_years", 0),
            "deal_type": deal.get("deal_type", "stabilized"),
        })
        deal["credit_policy_check"] = uw_result
        deal.setdefault("desk_outputs", {})["credit_underwriting"] = uw_result

        try:
            from agents.credit_memo_agent import CreditMemoAgent
            memo = CreditMemoAgent().generate_memo(deal)
            deal["credit_memo"] = memo
            deal["desk_outputs"]["credit_underwriting"]["memo"] = memo
        except Exception:
            deal["credit_memo"] = None

        deal["stage"] = "credit_complete"
        deal["stage_timestamp"] = datetime.utcnow().isoformat()
        return deal

    def run_rating(self, deal: dict) -> dict:
        """Stage 3: Rating Desk. Mirror Agent predictions + submission prep."""
        try:
            from agents.moodys_mirror import MoodysMirrorAgent
            from agents.sp_mirror import SPMirrorAgent

            rating_input = {
                "sector": deal.get("sector", "corporate"),
                "dscr": deal.get("dscr", 1.0),
                "leverage": deal.get("leverage", 5.0),
                "revenue": deal.get("revenue", 0),
                "ebitda": deal.get("ebitda", 0),
                "equity_pct": deal.get("equity_pct", 0.20),
                "enhancement": deal.get("enhancement", "none"),
                "management_quality": deal.get("management_quality", "adequate"),
                "market_position": deal.get("market_position", "satisfactory"),
                "revenue_diversity": deal.get("revenue_diversity", "moderate"),
                "days_cash_on_hand": deal.get("days_cash_on_hand", 90),
            }

            moodys = MoodysMirrorAgent()
            sp = SPMirrorAgent()

            m_scorecard = moodys.scorecard(rating_input)
            sp_brp = sp.business_risk_profile(rating_input)
            sp_frp = sp.financial_risk_profile(rating_input)

            deal["predicted_moodys"] = m_scorecard["predicted_rating"]
            deal["moodys_scorecard"] = m_scorecard
            deal["sp_assessment"] = {"business_risk": sp_brp, "financial_risk": sp_frp}
            deal["structural_levers"] = moodys.identify_levers(rating_input, m_scorecard)
            deal.setdefault("desk_outputs", {})["rating"] = {
                "moodys": m_scorecard,
                "sp": {"brp": sp_brp, "frp": sp_frp},
                "predicted_moodys": deal["predicted_moodys"],
            }
        except Exception as e:
            deal["rating_error"] = str(e)

        deal["stage"] = "rating_complete"
        deal["stage_timestamp"] = datetime.utcnow().isoformat()
        return deal

    def run_structuring(self, deal: dict) -> dict:
        """Stage 4: Structuring. Finalize covenants, terms."""
        covenant_package = self.intel.build_covenant_package(
            deal.get("deal_type", "ma_acquisition"),
            deal.get("credit_grade", "BBB"),
            deal.get("sector", "business_services"),
        )
        deal["covenant_package"] = covenant_package
        deal.setdefault("desk_outputs", {})["structuring"] = {
            "covenant_package": covenant_package,
            "bond_type": deal.get("bond_type", "taxable_senior_secured"),
            "amortization": deal.get("amortization", "io_then_amort"),
            "tenor_years": deal.get("tenor_years", 7),
        }
        deal["stage"] = "structuring_complete"
        deal["stage_timestamp"] = datetime.utcnow().isoformat()
        return deal

    def run_full_pipeline(self, deal: dict) -> dict:
        """Run the complete deal through all desks in sequence."""
        deal = self.run_intake(deal)
        deal = self.run_credit(deal)
        deal = self.run_rating(deal)
        deal = self.run_structuring(deal)
        deal["stage"] = "pipeline_complete"
        deal["pipeline_summary"] = {
            "bond_amount": deal.get("bond_amount"),
            "credit_grade": deal.get("credit_grade"),
            "predicted_moodys": deal.get("predicted_moodys"),
            "dscr": deal.get("dscr"),
            "leverage": deal.get("leverage"),
            "desks_completed": list(deal.get("desk_outputs", {}).keys()),
        }
        deal["stage_timestamp"] = datetime.utcnow().isoformat()
        return deal
