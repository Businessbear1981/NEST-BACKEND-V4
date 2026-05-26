"""
NEST Ramp Connector — Real Ramp API integration for construction draws,
soft costs, arrangement fees, T&E, and interchange rebates.

Base URL: https://api.ramp.com/developer/v1
Auth: Bearer token (OAuth 2.0)
Env: RAMP_API_KEY, RAMP_MODE (mock|live)

Three card programs per deal:
1. Construction Draws — bond-financed project spending
2. NEST Soft Costs — pre-close expenses (rating fees, legal, feasibility)
3. T&E Client Meetings — travel, hotel, meals for sponsor/site meetings
"""
from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://api.ramp.com/developer/v1"
RAMP_MODE = os.environ.get("RAMP_MODE", "mock")


def _headers() -> dict:
    key = os.environ.get("RAMP_API_KEY", "")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class RampConnector:
    """Real Ramp API client. Falls back to mock when RAMP_MODE=mock."""

    def __init__(self):
        self.mode = RAMP_MODE
        self.timeout = 15

    @property
    def is_live(self) -> bool:
        return self.mode == "live" and bool(os.environ.get("RAMP_API_KEY"))

    # ── Transactions ──────────────────────────────────────────

    def get_transactions(
        self,
        department_id: str = "",
        card_id: str = "",
        merchant_id: str = "",
        from_date: str = "",
        to_date: str = "",
        limit: int = 100,
    ) -> list[dict]:
        """GET /transactions — all card transactions with filters."""
        if not self.is_live:
            return []
        params: dict[str, Any] = {"page_size": limit}
        if department_id:
            params["department_id"] = department_id
        if card_id:
            params["card_id"] = card_id
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/transactions", headers=_headers(), params=params)
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /transactions error: %s", e)
            return []

    def get_transaction(self, transaction_id: str) -> dict | None:
        """GET /transactions/{id} — single transaction detail."""
        if not self.is_live:
            return None
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/transactions/{transaction_id}", headers=_headers())
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error("Ramp GET /transactions/%s error: %s", transaction_id, e)
            return None

    # ── Cards ─────────────────────────────────────────────────

    def list_cards(self, card_program_id: str = "") -> list[dict]:
        """GET /cards — all cards, optionally filtered by program."""
        if not self.is_live:
            return []
        params = {}
        if card_program_id:
            params["card_program_id"] = card_program_id
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/cards", headers=_headers(), params=params)
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /cards error: %s", e)
            return []

    def create_virtual_card(self, card_data: dict) -> dict | None:
        """POST /cards/deferred/virtual — issue a virtual card."""
        if not self.is_live:
            return {"status": "mock", "message": "RAMP_MODE=mock, card not created"}
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{BASE_URL}/cards/deferred/virtual", headers=_headers(), json=card_data)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error("Ramp POST /cards/deferred/virtual error: %s", e)
            return None

    def suspend_card(self, card_id: str) -> dict | None:
        """POST /cards/{id}/deferred/suspension — suspend a card."""
        if not self.is_live:
            return {"status": "mock"}
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{BASE_URL}/cards/{card_id}/deferred/suspension", headers=_headers())
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error("Ramp suspend card error: %s", e)
            return None

    # ── Card Programs ─────────────────────────────────────────

    def list_card_programs(self) -> list[dict]:
        """GET /card-programs — all card programs."""
        if not self.is_live:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/card-programs", headers=_headers())
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /card-programs error: %s", e)
            return []

    # ── Receipts ──────────────────────────────────────────────

    def list_receipts(self, transaction_id: str = "") -> list[dict]:
        """GET /receipts — all receipts, optionally filtered."""
        if not self.is_live:
            return []
        params = {}
        if transaction_id:
            params["transaction_id"] = transaction_id
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/receipts", headers=_headers(), params=params)
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /receipts error: %s", e)
            return []

    # ── Reimbursements ────────────────────────────────────────

    def list_reimbursements(self) -> list[dict]:
        """GET /reimbursements — all reimbursement requests."""
        if not self.is_live:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/reimbursements", headers=_headers())
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /reimbursements error: %s", e)
            return []

    def create_reimbursement(self, data: dict) -> dict | None:
        """POST /reimbursements — create a reimbursement request."""
        if not self.is_live:
            return {"status": "mock"}
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{BASE_URL}/reimbursements", headers=_headers(), json=data)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error("Ramp POST /reimbursements error: %s", e)
            return None

    # ── Budgets / Limits ──────────────────────────────────────

    def list_budgets(self) -> list[dict]:
        """GET /limits — all spending limits/budgets."""
        if not self.is_live:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/limits", headers=_headers())
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /limits error: %s", e)
            return []

    def create_budget(self, data: dict) -> dict | None:
        """POST /limits — create a new budget/spending limit."""
        if not self.is_live:
            return {"status": "mock"}
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(f"{BASE_URL}/limits", headers=_headers(), json=data)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error("Ramp POST /limits error: %s", e)
            return None

    # ── Accounting ────────────────────────────────────────────

    def list_gl_accounts(self) -> list[dict]:
        """GET /accounting/accounts — GL accounts for budget mapping."""
        if not self.is_live:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/accounting/accounts", headers=_headers())
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /accounting/accounts error: %s", e)
            return []

    def list_vendors(self) -> list[dict]:
        """GET /merchants — vendor/merchant database."""
        if not self.is_live:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/merchants", headers=_headers())
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /merchants error: %s", e)
            return []

    # ── Business / Balance ────────────────────────────────────

    def get_balance(self) -> dict | None:
        """GET /business/balance — account balance for escrow monitoring."""
        if not self.is_live:
            return None
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/business/balance", headers=_headers())
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error("Ramp GET /business/balance error: %s", e)
            return None

    # ── Departments ───────────────────────────────────────────

    def list_departments(self) -> list[dict]:
        """GET /departments — for categorizing spend by deal/program."""
        if not self.is_live:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.get(f"{BASE_URL}/departments", headers=_headers())
                r.raise_for_status()
                return r.json().get("data", [])
        except Exception as e:
            log.error("Ramp GET /departments error: %s", e)
            return []

    # ── NEST-Specific Aggregations ────────────────────────────

    def get_soft_costs(self, department_id: str = "") -> dict:
        """Pull soft cost transactions: rating fees, legal, feasibility, consulting."""
        soft_cost_mccs = ["8111", "8721", "7372", "7392", "8999"]  # legal, audit, tech, consulting, environmental
        txns = self.get_transactions(department_id=department_id)
        soft = [t for t in txns if t.get("merchant_category_code") in soft_cost_mccs]
        total = sum(t.get("amount", 0) for t in soft)
        return {
            "transactions": soft,
            "total": total,
            "count": len(soft),
            "rebate_earned": round(total * 0.015, 2),
            "categories": {
                "legal": sum(t["amount"] for t in soft if t.get("merchant_category_code") == "8111"),
                "audit": sum(t["amount"] for t in soft if t.get("merchant_category_code") == "8721"),
                "technology": sum(t["amount"] for t in soft if t.get("merchant_category_code") == "7372"),
                "consulting": sum(t["amount"] for t in soft if t.get("merchant_category_code") == "7392"),
                "environmental": sum(t["amount"] for t in soft if t.get("merchant_category_code") == "8999"),
            },
        }

    def get_te_costs(self, department_id: str = "") -> dict:
        """Pull T&E for client meetings: airlines, hotels, restaurants."""
        te_mccs = ["4511", "7011", "5812", "7512", "4121"]  # airlines, hotels, restaurants, car rental, taxi
        txns = self.get_transactions(department_id=department_id)
        te = [t for t in txns if t.get("merchant_category_code") in te_mccs]
        total = sum(t.get("amount", 0) for t in te)
        return {
            "transactions": te,
            "total": total,
            "count": len(te),
            "rebate_earned": round(total * 0.015, 2),
            "categories": {
                "airfare": sum(t["amount"] for t in te if t.get("merchant_category_code") == "4511"),
                "hotels": sum(t["amount"] for t in te if t.get("merchant_category_code") == "7011"),
                "meals": sum(t["amount"] for t in te if t.get("merchant_category_code") == "5812"),
                "ground_transport": sum(t["amount"] for t in te if t.get("merchant_category_code") in ("7512", "4121")),
            },
        }

    def get_arrangement_fees(self, department_id: str = "") -> dict:
        """Pull arrangement fee transactions: structuring, advisory, placement fees."""
        txns = self.get_transactions(department_id=department_id)
        # Arrangement fees are typically tagged with specific accounting categories
        arrangement = [t for t in txns if "arrangement" in (t.get("memo", "") or "").lower()
                       or "structuring" in (t.get("memo", "") or "").lower()
                       or "advisory" in (t.get("memo", "") or "").lower()]
        total = sum(t.get("amount", 0) for t in arrangement)
        return {
            "transactions": arrangement,
            "total": total,
            "count": len(arrangement),
        }

    def compute_rebate(self, department_id: str = "") -> dict:
        """Compute 1.5% interchange rebate across all eligible spend."""
        txns = self.get_transactions(department_id=department_id)
        total_spend = sum(t.get("amount", 0) for t in txns)
        rate = 0.015
        accrued = round(total_spend * rate, 2)
        return {
            "total_eligible_spend": round(total_spend, 2),
            "rebate_rate": rate,
            "rebate_accrued": accrued,
            "projected_annual": round(accrued * (365 / max(1, 180)), 2),
            "projected_36mo": round(accrued * (365 / max(1, 180)) * 3, 2),
            "computed_at": datetime.utcnow().isoformat(),
        }

    def status(self) -> dict:
        """Connection status and mode."""
        return {
            "mode": self.mode,
            "is_live": self.is_live,
            "api_key_set": bool(os.environ.get("RAMP_API_KEY")),
            "base_url": BASE_URL,
            "card_programs": {
                "construction_draws": "Construction draw spending against indenture budget categories",
                "soft_costs": "Pre-close soft costs — rating, legal, feasibility, consulting",
                "te_client": "T&E for client meetings — airfare, hotels, meals",
            },
        }
