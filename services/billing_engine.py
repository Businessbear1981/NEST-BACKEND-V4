"""
NEST Billing Engine — Fee calculation, invoicing, payment tracking.

Fee Architecture (from Bible Silo 5):
- Structuring Fee: 2-3% of par (earned at closing)
- Placement Fee: 0.5-1% of par (earned at pricing)
- Ongoing Administration: 50-75 bps annually (earned monthly, 30yr lifecycle)
- Commitment Fee: 25-50 bps (earned at commitment letter)
- Advisory Fee: negotiated (earned at engagement)

The fee is for:
1. Access to institutional bond market
2. Structural expertise — knowing which structure to use
3. Counterparty relationships — rating agencies, trustees, counsel
4. Execution — actually closing the deal
5. 30-year administration — recurring revenue engine

NOT for AI doing analysis in seconds. The AI enables two principals
to do the work of 40 people. The fee is market-standard institutional.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any


# Fee schedule per Operating Framework
FEE_SCHEDULE = {
    "structuring": {
        "rate_pct": 0.025,  # 2.5% of par (midpoint of 2-3%)
        "earned_at": "closing",
        "description": "Bond structuring, credit analysis, rating advisory, document coordination",
    },
    "placement": {
        "rate_pct": 0.0075,  # 0.75% of par (midpoint of 0.5-1%)
        "earned_at": "pricing",
        "description": "Investor matching, book building, pricing, allocation through BD partner",
    },
    "administration": {
        "rate_bps": 62.5,  # 62.5 bps annually (midpoint of 50-75)
        "earned_at": "monthly",
        "lifecycle_years": 30,
        "description": "Ongoing bond administration — debt service, covenant monitoring, EMMA filings, trustee coordination",
    },
    "commitment": {
        "rate_pct": 0.00375,  # 37.5 bps (midpoint of 25-50)
        "earned_at": "commitment_letter",
        "description": "Commitment to provide financing — locks in deal team capacity",
    },
    "advisory": {
        "rate_flat": 50_000,  # Minimum advisory fee
        "earned_at": "engagement",
        "description": "Financial advisory services — deal evaluation, capital structure recommendation",
    },
    "expense_reimbursement": {
        "description": "Pass-through of out-of-pocket expenses — rating agency fees, legal, travel",
        "earned_at": "closing",
    },
}

# Milestone-based billing schedule
BILLING_MILESTONES = [
    {"id": "engagement", "name": "Engagement Letter Executed", "fee_type": "advisory", "pct_of_total": 0},
    {"id": "commitment", "name": "Commitment Letter Issued", "fee_type": "commitment", "pct_of_total": 0.05},
    {"id": "rating", "name": "Rating Obtained", "fee_type": None, "pct_of_total": 0},
    {"id": "pricing", "name": "Bond Priced", "fee_type": "placement", "pct_of_total": 0.10},
    {"id": "closing", "name": "Bond Closed", "fee_type": "structuring", "pct_of_total": 0.85},
    {"id": "administration", "name": "Ongoing Administration", "fee_type": "administration", "pct_of_total": 0},
]


class BillingEngine:
    """Calculates fees, generates invoices, tracks payments."""

    def calculate_deal_fees(self, deal: dict) -> dict:
        """Calculate all fees for a deal based on bond amount."""
        par = deal.get("bond_amount", 0)

        structuring = round(par * FEE_SCHEDULE["structuring"]["rate_pct"])
        placement = round(par * FEE_SCHEDULE["placement"]["rate_pct"])
        commitment = round(par * FEE_SCHEDULE["commitment"]["rate_pct"])
        advisory = FEE_SCHEDULE["advisory"]["rate_flat"]
        admin_annual = round(par * FEE_SCHEDULE["administration"]["rate_bps"] / 10000)
        admin_monthly = round(admin_annual / 12)
        admin_lifecycle = admin_annual * FEE_SCHEDULE["administration"]["lifecycle_years"]

        total_closing = structuring + placement + commitment + advisory
        total_lifecycle = total_closing + admin_lifecycle

        return {
            "bond_amount": par,
            "fees": {
                "advisory": {"amount": advisory, "description": FEE_SCHEDULE["advisory"]["description"], "earned_at": "engagement"},
                "commitment": {"amount": commitment, "description": FEE_SCHEDULE["commitment"]["description"], "earned_at": "commitment_letter"},
                "placement": {"amount": placement, "description": FEE_SCHEDULE["placement"]["description"], "earned_at": "pricing"},
                "structuring": {"amount": structuring, "description": FEE_SCHEDULE["structuring"]["description"], "earned_at": "closing"},
            },
            "administration": {
                "annual": admin_annual,
                "monthly": admin_monthly,
                "lifecycle_years": 30,
                "lifecycle_total": admin_lifecycle,
                "description": FEE_SCHEDULE["administration"]["description"],
            },
            "totals": {
                "at_closing": total_closing,
                "annual_admin": admin_annual,
                "lifecycle_total": total_lifecycle,
                "as_pct_of_par": round(total_closing / par * 100, 2) if par else 0,
            },
            "milestones": [
                {**m, "amount": self._milestone_amount(m, deal)} for m in BILLING_MILESTONES
            ],
        }

    def _milestone_amount(self, milestone: dict, deal: dict) -> float:
        par = deal.get("bond_amount", 0)
        fee_type = milestone.get("fee_type")
        if not fee_type:
            return 0
        if fee_type == "advisory":
            return FEE_SCHEDULE["advisory"]["rate_flat"]
        if fee_type == "commitment":
            return round(par * FEE_SCHEDULE["commitment"]["rate_pct"])
        if fee_type == "placement":
            return round(par * FEE_SCHEDULE["placement"]["rate_pct"])
        if fee_type == "structuring":
            return round(par * FEE_SCHEDULE["structuring"]["rate_pct"])
        if fee_type == "administration":
            return round(par * FEE_SCHEDULE["administration"]["rate_bps"] / 10000)
        return 0

    def generate_invoice(self, deal: dict, milestone_id: str, invoice_number: str = None) -> dict:
        """Generate an invoice for a specific milestone."""
        fees = self.calculate_deal_fees(deal)
        milestone = next((m for m in fees["milestones"] if m["id"] == milestone_id), None)

        if not milestone:
            return {"error": f"Milestone {milestone_id} not found"}

        if not invoice_number:
            invoice_number = f"NEST-{deal.get('id', 'XXX')[:8].upper()}-{milestone_id[:4].upper()}-{datetime.utcnow().strftime('%Y%m')}"

        invoice = {
            "invoice_number": invoice_number,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "due_date": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "bill_to": {
                "name": deal.get("borrower", "Client"),
                "deal": deal.get("name", ""),
            },
            "from": {
                "name": "NEST Advisors",
                "address": "Sean Gilmore & Josh Edwards, Co-Founders",
                "entity": "Arden Edge Capital x Soparrow Capital",
            },
            "milestone": milestone["name"],
            "line_items": [],
            "subtotal": 0,
            "status": "draft",
        }

        # Build line items based on milestone
        if milestone_id == "engagement":
            invoice["line_items"].append({
                "description": "Financial Advisory Fee — deal evaluation, capital structure recommendation",
                "amount": FEE_SCHEDULE["advisory"]["rate_flat"],
            })
        elif milestone_id == "commitment":
            invoice["line_items"].append({
                "description": f"Commitment Fee — {FEE_SCHEDULE['commitment']['rate_pct']*100:.2f}% of ${deal.get('bond_amount',0):,.0f} par",
                "amount": round(deal.get("bond_amount", 0) * FEE_SCHEDULE["commitment"]["rate_pct"]),
            })
        elif milestone_id == "pricing":
            invoice["line_items"].append({
                "description": f"Placement Fee — {FEE_SCHEDULE['placement']['rate_pct']*100:.2f}% of ${deal.get('bond_amount',0):,.0f} par",
                "amount": round(deal.get("bond_amount", 0) * FEE_SCHEDULE["placement"]["rate_pct"]),
            })
        elif milestone_id == "closing":
            invoice["line_items"].append({
                "description": f"Structuring Fee — {FEE_SCHEDULE['structuring']['rate_pct']*100:.1f}% of ${deal.get('bond_amount',0):,.0f} par",
                "amount": round(deal.get("bond_amount", 0) * FEE_SCHEDULE["structuring"]["rate_pct"]),
            })
            # Add expense reimbursement placeholder
            invoice["line_items"].append({
                "description": "Expense Reimbursement — rating agency fees, legal, travel (actual costs)",
                "amount": 0,  # Filled in with actuals
                "note": "Amount to be confirmed with expense report",
            })

        invoice["subtotal"] = sum(item["amount"] for item in invoice["line_items"])
        return invoice

    def generate_admin_invoice(self, deal: dict, period: str) -> dict:
        """Generate monthly/quarterly administration invoice."""
        par = deal.get("bond_amount", 0)
        admin_annual = round(par * FEE_SCHEDULE["administration"]["rate_bps"] / 10000)
        admin_monthly = round(admin_annual / 12)

        return {
            "invoice_number": f"NEST-ADMIN-{deal.get('id', 'XXX')[:8].upper()}-{period}",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "due_date": (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d"),
            "bill_to": {"name": deal.get("borrower", "Client"), "deal": deal.get("name", "")},
            "from": {"name": "NEST Advisors"},
            "period": period,
            "line_items": [
                {
                    "description": f"Bond Administration — {period}",
                    "detail": "Debt service calculation, covenant monitoring, EMMA filings, trustee coordination, reserve management",
                    "amount": admin_monthly,
                    "rate": f"{FEE_SCHEDULE['administration']['rate_bps']} bps annually on ${par:,.0f} par",
                },
            ],
            "subtotal": admin_monthly,
            "status": "draft",
        }

    def deal_economics(self, deal: dict) -> dict:
        """Full economic analysis of a deal for NEST — what do we earn?"""
        fees = self.calculate_deal_fees(deal)
        par = deal.get("bond_amount", 0)

        # Ramp rebate (if construction deal with P-card)
        ramp_eligible_spend = deal.get("total_project_cost", 0) * 0.60  # ~60% of TPC flows through cards
        ramp_rebate_annual = round(ramp_eligible_spend * 0.015 / 3)  # 1.5% spread over construction period
        ramp_rebate_total = round(ramp_eligible_spend * 0.015)

        return {
            "deal": deal.get("name", ""),
            "bond_amount": par,
            "revenue_at_closing": {
                "structuring_fee": fees["fees"]["structuring"]["amount"],
                "placement_fee": fees["fees"]["placement"]["amount"],
                "commitment_fee": fees["fees"]["commitment"]["amount"],
                "advisory_fee": fees["fees"]["advisory"]["amount"],
                "total": fees["totals"]["at_closing"],
            },
            "recurring_revenue": {
                "administration_annual": fees["administration"]["annual"],
                "administration_monthly": fees["administration"]["monthly"],
                "administration_30yr": fees["administration"]["lifecycle_total"],
            },
            "ramp_rebate": {
                "eligible_spend": round(ramp_eligible_spend),
                "rebate_rate": 0.015,
                "annual_estimate": ramp_rebate_annual,
                "total_estimate": ramp_rebate_total,
            },
            "total_economics": {
                "year_1": fees["totals"]["at_closing"] + fees["administration"]["annual"] + ramp_rebate_annual,
                "year_2_onwards": fees["administration"]["annual"],
                "lifetime_30yr": fees["totals"]["lifecycle_total"] + ramp_rebate_total,
            },
        }
