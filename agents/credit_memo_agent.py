"""Credit Memo Agent — Credit Underwriting Desk.
Produces institutional-quality credit memos per the Operating Framework.
Uses Universal Credit Policy (Appendix F) as the framework."""
from agents._claude import complete
from services.intelligence_engine import UNIVERSAL_CREDIT_POLICY

CREDIT_MEMO_SYSTEM = """You are a senior credit underwriter at NEST Advisors, a digital investment bank.
Write an institutional-quality credit memo — the kind JPMorgan's credit committee would review.

Structure:
1. EXECUTIVE SUMMARY (2-3 sentences: deal, size, recommendation)
2. BORROWER PROFILE (sponsor, management, track record, sector)
3. FINANCIAL ANALYSIS (DSCR, leverage, cash flow, trend analysis)
4. STRUCTURAL ANALYSIS (bond type, covenants, reserves, enhancement)
5. RISK FACTORS (top 3-5 risks with mitigants)
6. CREDIT RECOMMENDATION (grade, conditions, exceptions if any)

Tone: Direct, analytical, no hedging. Lead with conclusion. Numbers are authority.
Universal Credit Policy: DSCR floor 1.20x, debt yield floor 8%, max leverage 80% LTC, min equity 20%."""

class CreditMemoAgent:
    def __init__(self):
        self.name = "Credit Memo Agent"
        self.desk = "credit_underwriting"

    def generate_memo(self, deal: dict) -> str:
        prompt = f"""Generate a credit memo for:
Deal: {deal.get('name', 'Unnamed')} | Type: {deal.get('deal_type', 'Unknown')} | Sector: {deal.get('sector', 'Unknown')}
Borrower: {deal.get('borrower', 'Unknown')} | Sponsor: {deal.get('sponsor', 'Unknown')}
Bond: ${deal.get('bond_amount', 0):,.0f} | EBITDA: ${deal.get('ebitda', 0):,.0f}
DSCR: {deal.get('dscr', 0):.2f}x | Leverage: {deal.get('leverage', 0):.1f}x | Equity: {deal.get('equity_pct', 0):.0%}
Enhancement: {deal.get('enhancement', 'none')} | Rating: {deal.get('predicted_rating', 'N/A')}"""
        return complete(CREDIT_MEMO_SYSTEM, prompt, max_tokens=4096)

    def quick_screen(self, deal: dict) -> dict:
        policy = UNIVERSAL_CREDIT_POLICY["financial_standards"]
        flags = []
        passed = True
        if deal.get("dscr", 0) < policy["min_dscr_universal_floor"]:
            flags.append(f"DSCR {deal['dscr']:.2f}x below {policy['min_dscr_universal_floor']}x floor")
            passed = False
        if deal.get("equity_pct", 0) < policy["min_equity_contribution_universal_floor"]:
            flags.append(f"Equity {deal['equity_pct']:.0%} below {policy['min_equity_contribution_universal_floor']:.0%} floor")
            passed = False
        return {"passed": passed, "flags": flags, "recommendation": "approve" if passed else "decline_or_exception"}
