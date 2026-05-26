"""
NEST Database Service — Supabase client abstraction layer.

All DB access goes through this module. The app imports services.database,
never supabase or boto3 directly. This makes the Supabase -> AWS RDS migration
a config change, not a rewrite.
"""
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class DatabaseService:
    """Thin wrapper over Supabase REST API."""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._configured = bool(self.url and self.key)

    @property
    def configured(self):
        return self._configured

    def _headers(self):
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _api(self, path):
        return f"{self.url}/rest/v1/{path}"

    # ── Generic CRUD ────────────────────────────────────────────

    def select(self, table, params=None, single=False):
        """SELECT from table with optional query params."""
        if not self._configured:
            return None
        headers = self._headers()
        if single:
            headers["Accept"] = "application/vnd.pgrst.object+json"
        try:
            r = httpx.get(self._api(table), headers=headers, params=params or {}, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return [] if not single else None

    def insert(self, table, data):
        """INSERT row(s). Returns inserted row(s)."""
        if not self._configured:
            return None
        try:
            r = httpx.post(self._api(table), headers=self._headers(), json=data, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def update(self, table, match, data):
        """UPDATE rows matching filter. match = {"id": "eq.xxx"}"""
        if not self._configured:
            return None
        try:
            r = httpx.patch(self._api(table), headers=self._headers(), params=match, json=data, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def upsert(self, table, data):
        """UPSERT (insert or update on conflict)."""
        if not self._configured:
            return None
        headers = self._headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        try:
            r = httpx.post(self._api(table), headers=headers, json=data, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def delete(self, table, match):
        """DELETE rows matching filter."""
        if not self._configured:
            return None
        try:
            r = httpx.delete(self._api(table), headers=self._headers(), params=match, timeout=10)
            r.raise_for_status()
            return True
        except Exception:
            return False

    # ── Domain Helpers ──────────────────────────────────────────

    def save_modeling_result(self, deal_id, model_type, inputs, outputs,
                             irr=None, npv=None, dscr_min=None, dscr_avg=None,
                             is_feasible=False, run_by=None):
        """Persist an agent modeling result (Maxwell, Prometheus, etc.)."""
        # Get next version number
        existing = self.select("modeling_results", {
            "deal_id": f"eq.{deal_id}",
            "model_type": f"eq.{model_type}",
            "order": "version.desc",
            "limit": "1",
        })
        version = 1
        if existing and isinstance(existing, list) and len(existing) > 0:
            version = existing[0].get("version", 0) + 1

        return self.insert("modeling_results", {
            "deal_id": deal_id,
            "model_type": model_type,
            "version": version,
            "inputs": inputs,
            "outputs": outputs,
            "irr": irr,
            "npv": npv,
            "dscr_min": dscr_min,
            "dscr_avg": dscr_avg,
            "is_feasible": is_feasible,
            "run_by": run_by,
        })

    def save_risk_score(self, deal_id, scores, grade=None):
        """Persist a Sentinel risk assessment."""
        return self.insert("risk_scores", {
            "deal_id": deal_id,
            "overall_score": scores.get("overall", 0),
            "credit_risk": scores.get("credit", 0),
            "market_risk": scores.get("market", 0),
            "construction_risk": scores.get("construction", 0),
            "legal_risk": scores.get("legal", 0),
            "operational_risk": scores.get("operational", 0),
            "environmental_risk": scores.get("environmental", 0),
            "political_risk": scores.get("political", 0),
            "grade": grade,
        })

    def save_risk_alert(self, deal_id, severity, category, title, description=None, risk_score_id=None):
        """Persist a risk alert."""
        return self.insert("risk_alerts", {
            "deal_id": deal_id,
            "risk_score_id": risk_score_id,
            "severity": severity,
            "category": category,
            "title": title,
            "description": description,
        })

    def update_agent_status(self, agent_name, status, error_log=None):
        """Update agent run status in the agents table."""
        data = {
            "status": status,
            "last_run_at": datetime.utcnow().isoformat(),
        }
        if status == "active":
            # Increment run count via raw — use upsert workaround
            existing = self.select("agents", {"name": f"eq.{agent_name}"})
            if existing and isinstance(existing, list) and len(existing) > 0:
                data["run_count"] = existing[0].get("run_count", 0) + 1
        if error_log:
            data["error_log"] = error_log
        return self.update("agents", {"name": f"eq.{agent_name}"}, data)

    def save_lender_match(self, deal_id, lender_id, score, match_reasons=None,
                           proposed_rate=None, proposed_amount=None):
        """Persist a Lender Scout match."""
        return self.insert("lender_matches", {
            "deal_id": deal_id,
            "lender_id": lender_id,
            "score": score,
            "match_reasons": match_reasons or [],
            "proposed_rate": proposed_rate,
            "proposed_amount": proposed_amount,
        })

    def save_investor(self, data):
        """Upsert an investor record for Sterling."""
        return self.upsert("investors", data)


# Singleton
db = DatabaseService()
