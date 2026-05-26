"""Refunding Identification Agent — Surveillance Desk.
Identifies bonds where current rates produce NPV savings through refunding.
Per Operating Framework: current refunding within 90 days still permitted after TCJA."""
from agents._claude import complete

class RefundingAgent:
    def __init__(self):
        self.name = "Refunding ID Agent"
        self.desk = "surveillance"

    def identify_refunding_candidates(self, portfolio: list[dict]) -> list[dict]:
        candidates = []
        for bond in portfolio:
            coupon = bond.get("coupon_rate", 0)
            current_rate = bond.get("current_market_rate", coupon)
            par = bond.get("par_amount", 0)
            call_date = bond.get("next_call_date", "")
            remaining_years = bond.get("remaining_years", 0)
            rate_savings_bps = (coupon - current_rate) * 100
            if rate_savings_bps < 25:
                continue
            annual_savings = par * (coupon - current_rate) / 100
            npv_savings = annual_savings * remaining_years * 0.85
            pv_savings_pct = (npv_savings / par) * 100 if par else 0
            if pv_savings_pct >= 3.0:
                candidates.append({
                    "bond": bond,
                    "rate_savings_bps": round(rate_savings_bps, 1),
                    "annual_savings": round(annual_savings),
                    "npv_savings": round(npv_savings),
                    "pv_savings_pct": round(pv_savings_pct, 2),
                    "call_date": call_date,
                    "recommendation": "refund" if pv_savings_pct >= 5.0 else "monitor",
                    "urgency": "high" if pv_savings_pct >= 7.0 else "medium" if pv_savings_pct >= 5.0 else "low",
                })
        candidates.sort(key=lambda x: x["pv_savings_pct"], reverse=True)
        return candidates

    def refunding_memo(self, candidate: dict) -> str:
        bond = candidate.get("bond", {})
        prompt = f"""Write a refunding recommendation memo for:
Bond: {bond.get('issuer', 'Unknown')} — {bond.get('cusip', '')}
Current coupon: {bond.get('coupon_rate', 0)}%
Current market rate: {bond.get('current_market_rate', 0)}%
Par amount: ${bond.get('par_amount', 0):,.0f}
Rate savings: {candidate.get('rate_savings_bps', 0)} bps
NPV savings: ${candidate.get('npv_savings', 0):,.0f} ({candidate.get('pv_savings_pct', 0)}% of par)
Next call date: {candidate.get('call_date', 'N/A')}
Cover: economic analysis, execution timeline, risks, recommendation."""
        return complete("You are a senior bond refunding analyst at NEST Advisors. Write a concise, direct memo. No hedging.", prompt, max_tokens=2048)
