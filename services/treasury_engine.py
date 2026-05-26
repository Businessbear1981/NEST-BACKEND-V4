"""
NEST Treasury Engine — Ramp P-Card mock/live adapter.
Generates realistic data mirroring Ramp's API schema.
Switch via RAMP_MODE=mock|live env var.
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from typing import Any

_MODE = os.environ.get("RAMP_MODE", "mock")

# ── Budget categories for a $487M construction project ────────────────
BUDGET_CATEGORIES = [
    {"id": "cat_gc", "name": "General Contractor", "budgeted": 312_000_000},
    {"id": "cat_arch", "name": "Architecture & Engineering", "budgeted": 28_500_000},
    {"id": "cat_legal", "name": "Legal & Counsel", "budgeted": 8_200_000},
    {"id": "cat_rating", "name": "Rating & Grading", "budgeted": 4_800_000},
    {"id": "cat_audit", "name": "Financial Audit", "budgeted": 3_600_000},
    {"id": "cat_insurance", "name": "Insurance & Surety", "budgeted": 18_400_000},
    {"id": "cat_permits", "name": "Permits & Fees", "budgeted": 6_100_000},
    {"id": "cat_hosting", "name": "Technology & Hosting", "budgeted": 2_400_000},
    {"id": "cat_te", "name": "Travel & Entertainment", "budgeted": 1_800_000},
    {"id": "cat_consulting", "name": "Consulting & Advisory", "budgeted": 9_200_000},
    {"id": "cat_enviro", "name": "Environmental & Survey", "budgeted": 5_700_000},
    {"id": "cat_contingency", "name": "Contingency Reserve", "budgeted": 86_300_000},
]

TOTAL_BUDGET = sum(c["budgeted"] for c in BUDGET_CATEGORIES)  # $487M

# ── Vendor roster for virtual cards ───────────────────────────────────
VENDORS = [
    {"name": "Turner Construction", "category_id": "cat_gc", "mcc": "1520"},
    {"name": "Skanska USA", "category_id": "cat_gc", "mcc": "1520"},
    {"name": "AECOM", "category_id": "cat_arch", "mcc": "8711"},
    {"name": "Gensler", "category_id": "cat_arch", "mcc": "8711"},
    {"name": "Greenberg Traurig LLP", "category_id": "cat_legal", "mcc": "8111"},
    {"name": "Orrick Herrington", "category_id": "cat_legal", "mcc": "8111"},
    {"name": "Moody's Investors Service", "category_id": "cat_rating", "mcc": "7372"},
    {"name": "S&P Global Ratings", "category_id": "cat_rating", "mcc": "7372"},
    {"name": "Deloitte & Touche", "category_id": "cat_audit", "mcc": "8721"},
    {"name": "KPMG LLP", "category_id": "cat_audit", "mcc": "8721"},
    {"name": "Hylant Group", "category_id": "cat_insurance", "mcc": "6300"},
    {"name": "Marsh McLennan", "category_id": "cat_insurance", "mcc": "6300"},
    {"name": "AWS", "category_id": "cat_hosting", "mcc": "7372"},
    {"name": "Vercel Inc", "category_id": "cat_hosting", "mcc": "7372"},
    {"name": "McKinsey & Company", "category_id": "cat_consulting", "mcc": "7392"},
    {"name": "Terracon Consultants", "category_id": "cat_enviro", "mcc": "8999"},
    {"name": "United Airlines", "category_id": "cat_te", "mcc": "4511"},
    {"name": "Hilton Hotels", "category_id": "cat_te", "mcc": "7011"},
]

# ── NEST pre-close soft costs ─────────────────────────────────────────
NEST_SOFT_COSTS = [
    {"vendor": "Moody's Investors Service", "category": "Rating & Grading", "amount": 850_000, "date": "2025-11-15"},
    {"vendor": "S&P Global Ratings", "category": "Rating & Grading", "amount": 720_000, "date": "2025-12-01"},
    {"vendor": "Greenberg Traurig LLP", "category": "Legal & Counsel", "amount": 480_000, "date": "2025-10-20"},
    {"vendor": "Orrick Herrington", "category": "Legal & Counsel", "amount": 340_000, "date": "2025-11-05"},
    {"vendor": "Deloitte & Touche", "category": "Financial Audit", "amount": 290_000, "date": "2025-12-10"},
    {"vendor": "AWS", "category": "Technology & Hosting", "amount": 48_000, "date": "2025-09-01"},
    {"vendor": "Vercel Inc", "category": "Technology & Hosting", "amount": 12_000, "date": "2025-09-15"},
    {"vendor": "McKinsey & Company", "category": "Consulting & Advisory", "amount": 380_000, "date": "2025-11-20"},
    {"vendor": "United Airlines", "category": "Travel & Entertainment", "amount": 24_500, "date": "2026-01-08"},
    {"vendor": "Hilton Hotels", "category": "Travel & Entertainment", "amount": 18_200, "date": "2026-01-09"},
]


def _ts(offset_days: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:04d}"


class TreasuryEngine:
    """Generates Ramp-schema mock data for a deal. Stateless — every call rebuilds from seed."""

    def __init__(self) -> None:
        self._seed = 42

    # ── Public API ────────────────────────────────────────────────────

    def overview(self, deal_id: str) -> dict[str, Any]:
        cards = self.cards(deal_id)
        txns = self.transactions(deal_id)
        rebate = self.rebate(deal_id)
        total_spent = sum(t["amount"] for t in txns)
        total_loaded = sum(pf["amount"] for pf in self.prefund_history(deal_id))
        return {
            "deal_id": deal_id,
            "total_budget": TOTAL_BUDGET,
            "total_loaded": total_loaded,
            "total_spent": total_spent,
            "available_balance": total_loaded - total_spent,
            "escrow_source": "Client prefunded escrow — auto-pay on statement cycle",
            "active_cards": len([c for c in cards if c["state"] == "ACTIVE"]),
            "total_transactions": len(txns),
            "rebate_accrued": rebate["accrued"],
            "receipt_match_rate": 0.973,
        }

    def transactions(self, deal_id: str) -> list[dict[str, Any]]:
        rng = random.Random(self._seed)
        txns: list[dict[str, Any]] = []
        for i in range(240):
            vendor = rng.choice(VENDORS)
            cat = next(c for c in BUDGET_CATEGORIES if c["id"] == vendor["category_id"])
            base = {
                "cat_gc": (800_000, 4_200_000),
                "cat_arch": (50_000, 400_000),
                "cat_legal": (25_000, 180_000),
                "cat_rating": (75_000, 250_000),
                "cat_audit": (30_000, 120_000),
                "cat_insurance": (40_000, 350_000),
                "cat_permits": (5_000, 80_000),
                "cat_hosting": (2_000, 24_000),
                "cat_te": (500, 8_000),
                "cat_consulting": (20_000, 150_000),
                "cat_enviro": (10_000, 90_000),
                "cat_contingency": (10_000, 200_000),
            }.get(vendor["category_id"], (1_000, 50_000))
            amount = round(rng.uniform(base[0], base[1]), 2)
            days_ago = rng.randint(1, 180)
            has_receipt = rng.random() < 0.973
            txns.append({
                "id": _id("txn", i),
                "card_id": _id("card", VENDORS.index(vendor)),
                "merchant_name": vendor["name"],
                "merchant_category_code": vendor["mcc"],
                "amount": amount,
                "currency": "USD",
                "state": rng.choice(["CLEARED", "CLEARED", "CLEARED", "PENDING"]),
                "receipts": [{"id": _id("rcpt", i), "receipt_url": f"/receipts/{_id('rcpt', i)}.pdf"}] if has_receipt else [],
                "memo": f"{cat['name']} — {vendor['name']}",
                "category": {"id": vendor["category_id"], "name": cat["name"]},
                "accounting_categories": [{"id": f"ac_{vendor['category_id']}", "name": f"Construction — {cat['name']}"}],
                "created_at": _ts(days_ago),
                "settled_at": _ts(days_ago - 2) if rng.random() < 0.9 else None,
            })
        txns.sort(key=lambda t: t["created_at"], reverse=True)
        return txns

    def cards(self, deal_id: str) -> list[dict[str, Any]]:
        rng = random.Random(self._seed + 1)
        result: list[dict[str, Any]] = []
        for i, vendor in enumerate(VENDORS):
            cat = next(c for c in BUDGET_CATEGORIES if c["id"] == vendor["category_id"])
            limit = cat["budgeted"] // max(1, sum(1 for v in VENDORS if v["category_id"] == vendor["category_id"]))
            spent = round(limit * rng.uniform(0.15, 0.55), 2)
            result.append({
                "id": _id("card", i),
                "display_name": f"{vendor['name']} — {cat['name']}",
                "card_program_id": "prog_nest_001",
                "last_four": f"{rng.randint(1000, 9999)}",
                "state": "ACTIVE",
                "spending_restrictions": {
                    "amount": float(limit),
                    "interval": "TOTAL",
                    "categories": [vendor["mcc"]],
                    "blocked_categories": [],
                },
                "total_spent": spent,
                "available_balance": round(limit - spent, 2),
                "card_holder": {"first_name": "Sean", "last_name": "Gilmore"},
            })
        return result

    def budget(self, deal_id: str) -> list[dict[str, Any]]:
        txns = self.transactions(deal_id)
        spent_by_cat: dict[str, float] = {}
        for t in txns:
            cid = t["category"]["id"]
            spent_by_cat[cid] = spent_by_cat.get(cid, 0) + t["amount"]

        draws = self.prefund_history(deal_id)
        drawn_total = sum(pf["amount"] for pf in draws)
        result: list[dict[str, Any]] = []
        for cat in BUDGET_CATEGORIES:
            spent = round(spent_by_cat.get(cat["id"], 0), 2)
            drawn = round(drawn_total * (cat["budgeted"] / TOTAL_BUDGET), 2)
            remaining = round(cat["budgeted"] - spent, 2)
            variance_pct = round(((spent / max(drawn, 1)) - 1) * 100, 1) if drawn > 0 else 0
            status = "red" if variance_pct > 5 else "amber" if variance_pct > 0 else "green"
            result.append({
                "category_id": cat["id"],
                "category_name": cat["name"],
                "budgeted": cat["budgeted"],
                "drawn": drawn,
                "spent": spent,
                "remaining": remaining,
                "variance_pct": variance_pct,
                "status": status,
            })
        return result

    def prefund_history(self, deal_id: str) -> list[dict[str, Any]]:
        return [
            {"id": _id("pf", i), "deal_id": deal_id, "draw_id": _id("draw", i),
             "amount": amt, "funded_at": _ts(180 - i * 30),
             "card_program_id": "prog_nest_001", "status": "funded",
             "approval_id": _id("appr", i)}
            for i, amt in enumerate([
                8_200_000, 9_400_000, 11_800_000, 10_600_000, 12_100_000, 8_900_000,
            ])
        ]

    def reconciliation(self, deal_id: str) -> list[dict[str, Any]]:
        prefunds = self.prefund_history(deal_id)
        txns = self.transactions(deal_id)
        rng = random.Random(self._seed + 3)
        result: list[dict[str, Any]] = []
        for pf in prefunds:
            matched_txns = [t for t in rng.sample(txns, min(40, len(txns)))]
            matched_total = sum(t["amount"] for t in matched_txns)
            result.append({
                "prefund_id": pf["id"],
                "draw_id": pf["draw_id"],
                "draw_amount": pf["amount"],
                "matched_spend": round(matched_total, 2),
                "unreconciled": round(pf["amount"] - matched_total, 2),
                "transaction_count": len(matched_txns),
                "status": "reconciled" if abs(pf["amount"] - matched_total) < 50_000 else "pending",
            })
        return result

    def rebate(self, deal_id: str) -> dict[str, Any]:
        txns = self.transactions(deal_id)
        total_spend = sum(t["amount"] for t in txns)
        rate = 0.015  # 1.5%
        accrued = round(total_spend * rate, 2)
        projected_annual = round(accrued * (365 / 180), 2)
        return {
            "deal_id": deal_id,
            "rate": rate,
            "total_eligible_spend": round(total_spend, 2),
            "accrued": accrued,
            "realized": round(accrued * 0.6, 2),
            "projected_36mo": round(projected_annual * 3, 2),
        }

    def nest_soft_costs(self) -> dict[str, Any]:
        total = sum(c["amount"] for c in NEST_SOFT_COSTS)
        rebate = round(total * 0.015, 2)
        return {
            "line_items": NEST_SOFT_COSTS,
            "total_fronted": total,
            "rebate_earned": rebate,
            "reimbursement_status": "pending",
        }

    def nest_reimbursement(self, deal_id: str) -> dict[str, Any]:
        costs = self.nest_soft_costs()
        return {
            "deal_id": deal_id,
            "invoice_number": "NEST-REIMB-2026-001",
            "line_items": costs["line_items"],
            "subtotal": costs["total_fronted"],
            "status": "draft",
            "generated_at": _ts(0),
        }

    def portfolio(self) -> dict[str, Any]:
        """Portfolio-wide treasury economics across all deals."""
        nest = self.nest_soft_costs()
        deals = ["deal-1", "deal-2", "deal-3"]
        total_spend = 0.0
        total_rebate = 0.0
        for d in deals:
            r = self.rebate(d)
            total_spend += r["total_eligible_spend"]
            total_rebate += r["accrued"]
        return {
            "active_deals": len(deals),
            "total_managed_spend": round(total_spend, 2),
            "total_rebate_accrued": round(total_rebate, 2),
            "nest_soft_cost_rebate": nest["rebate_earned"],
            "combined_rebate": round(total_rebate + nest["rebate_earned"], 2),
            "traditional_savings": {
                "manual_reconciliation_hours_eliminated": 1_200,
                "estimated_labor_savings": 180_000,
                "misallocation_risk_reduction": "97.3% auto-categorized",
            },
        }
