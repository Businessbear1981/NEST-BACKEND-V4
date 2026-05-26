"""
NEST Bridge Lending Fund.
Parallel to bonds. Finances soft costs, packaging, surety premiums.
NEST takes 10-15% equity in perpetuity. Zero risk — bond takes out.
Bridge loan is repaid from bond proceeds at closing.
NEST keeps the equity forever.
"""
import uuid
from datetime import datetime


class BridgeFund:

    FUND_PARAMS = {
        "target_aum_usd": 25_000_000,
        "max_single_loan_pct": 20,
        "term_months_range": (6, 9),
        "interest_rate_pct": 0,
        "equity_kicker_pct_range": (10, 15),
        "equity_type": "perpetual_preferred_or_warrant",
        "takeout": "bond_proceeds_at_closing",
        "risk_level": "near_zero",
        "risk_note": "Bond takes out bridge at closing. Secured by same collateral as bond.",
        "eligible_uses": ["packaging_fees", "soft_costs", "surety_premiums",
                          "legal_fees", "pre_development_costs", "architect_fees"],
        "ineligible_uses": ["land_acquisition", "construction_hard_costs"],
    }

    def __init__(self):
        self.loans = {}
        self.total_deployed = 0
        self.total_equity_positions = []

    def underwrite_bridge(self, deal: dict, amount_usd: float,
                          use_of_proceeds: str) -> dict:
        max_loan = round(self.FUND_PARAMS["target_aum_usd"] * self.FUND_PARAMS["max_single_loan_pct"] / 100)

        if amount_usd > max_loan:
            return {"error": f"Loan ${amount_usd:,.0f} exceeds max single loan ${max_loan:,.0f} ({self.FUND_PARAMS['max_single_loan_pct']}% of fund)",
                    "max_single_loan_usd": max_loan}

        if use_of_proceeds in self.FUND_PARAMS["ineligible_uses"]:
            return {"error": f"'{use_of_proceeds}' is ineligible for bridge lending. Eligible: {', '.join(self.FUND_PARAMS['eligible_uses'])}"}

        available = self.FUND_PARAMS["target_aum_usd"] - self.total_deployed
        if amount_usd > available:
            return {"error": f"Insufficient fund capacity. Available: ${available:,.0f}, requested: ${amount_usd:,.0f}"}

        tpc = deal.get("total_project_cost_usd", amount_usd * 10)
        bond_amount = deal.get("bond_amount_usd", tpc * 0.82)
        equity_pct = 12.5

        loan_id = f"bridge_{uuid.uuid4().hex[:8]}"
        loan = {
            "loan_id": loan_id,
            "deal_name": deal.get("name", "Unnamed"),
            "deal_id": deal.get("deal_id", ""),
            "amount_usd": amount_usd,
            "use_of_proceeds": use_of_proceeds,
            "interest_rate_pct": self.FUND_PARAMS["interest_rate_pct"],
            "term_months": 9,
            "equity_kicker_pct": equity_pct,
            "equity_type": self.FUND_PARAMS["equity_type"],
            "takeout_source": "bond_proceeds",
            "takeout_bond_amount_usd": bond_amount,
            "collateral": "Same collateral as bond — senior mortgage + trust estate",
            "risk_assessment": {
                "risk_level": self.FUND_PARAMS["risk_level"],
                "takeout_certainty": "high" if deal.get("presales_pct", 0) >= 50 else "medium",
                "collateral_coverage": round(tpc / amount_usd, 1) if amount_usd else 0,
                "bond_takeout_multiple": round(bond_amount / amount_usd, 1) if amount_usd else 0,
            },
            "nest_economics": {
                "interest_income_usd": 0,
                "equity_pct_acquired": equity_pct,
                "estimated_equity_value_at_stabilization_usd": round(tpc * 1.5 * equity_pct / 100),
                "cost_basis_usd": amount_usd,
                "roi_at_stabilization_pct": round((tpc * 1.5 * equity_pct / 100) / amount_usd * 100, 1) if amount_usd else 0,
            },
            "status": "approved",
            "approved_date": datetime.utcnow().isoformat(),
            "maturity_date": None,
        }

        self.loans[loan_id] = loan
        self.total_deployed += amount_usd
        self.total_equity_positions.append({
            "loan_id": loan_id, "deal_name": deal.get("name", ""),
            "equity_pct": equity_pct, "cost_basis_usd": amount_usd,
        })

        return loan

    def calculate_equity_value(self, deal: dict, equity_pct: float,
                               exit_ev: float) -> dict:
        equity_value = round(exit_ev * equity_pct / 100)
        cost_basis = deal.get("bridge_amount_usd", 0)
        gain = equity_value - cost_basis

        scenarios = []
        for mult_name, mult in [("bear", 0.7), ("base", 1.0), ("bull", 1.3)]:
            ev = round(exit_ev * mult)
            val = round(ev * equity_pct / 100)
            scenarios.append({
                "scenario": mult_name,
                "exit_ev_usd": ev,
                "equity_value_usd": val,
                "gain_usd": val - cost_basis,
                "roi_pct": round((val - cost_basis) / cost_basis * 100, 1) if cost_basis else 0,
            })

        return {
            "equity_pct": equity_pct,
            "exit_ev_usd": exit_ev,
            "equity_value_usd": equity_value,
            "cost_basis_usd": cost_basis,
            "gain_usd": gain,
            "roi_pct": round(gain / cost_basis * 100, 1) if cost_basis else 0,
            "scenarios": scenarios,
            "perpetual": True,
            "note": "NEST holds equity in perpetuity. No expiration. Participates in all future value creation.",
        }

    def portfolio_dashboard(self) -> dict:
        active_loans = {k: v for k, v in self.loans.items() if v["status"] in ["approved", "funded"]}
        repaid_loans = {k: v for k, v in self.loans.items() if v["status"] == "repaid"}

        total_active = sum(l["amount_usd"] for l in active_loans.values())
        total_repaid = sum(l["amount_usd"] for l in repaid_loans.values())
        available = self.FUND_PARAMS["target_aum_usd"] - total_active

        total_equity_value = sum(
            ep.get("cost_basis_usd", 0) * 3
            for ep in self.total_equity_positions
        )

        return {
            "fund_aum_usd": self.FUND_PARAMS["target_aum_usd"],
            "capital_deployed_usd": total_active,
            "capital_available_usd": available,
            "utilization_pct": round(total_active / self.FUND_PARAMS["target_aum_usd"] * 100, 1) if self.FUND_PARAMS["target_aum_usd"] else 0,
            "active_loans": len(active_loans),
            "repaid_loans": len(repaid_loans),
            "total_loans_originated": len(self.loans),
            "total_repaid_usd": total_repaid,
            "equity_positions": len(self.total_equity_positions),
            "estimated_equity_portfolio_value_usd": total_equity_value,
            "active_loan_details": list(active_loans.values()),
            "equity_position_details": self.total_equity_positions,
            "fund_params": self.FUND_PARAMS,
        }

    def repay_loan(self, loan_id: str, repayment_source: str = "bond_proceeds") -> dict:
        loan = self.loans.get(loan_id)
        if not loan:
            return {"error": "Loan not found"}
        if loan["status"] == "repaid":
            return {"error": "Loan already repaid"}

        loan["status"] = "repaid"
        loan["repaid_date"] = datetime.utcnow().isoformat()
        loan["repayment_source"] = repayment_source
        self.total_deployed -= loan["amount_usd"]

        return {
            "loan_id": loan_id,
            "amount_repaid_usd": loan["amount_usd"],
            "repayment_source": repayment_source,
            "equity_retained": True,
            "equity_pct": loan["equity_kicker_pct"],
            "note": "Principal repaid from bond proceeds. NEST retains equity position in perpetuity.",
        }


bridge_fund = BridgeFund()
