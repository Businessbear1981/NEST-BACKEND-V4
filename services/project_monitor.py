"""
NEST Project Monitor
Tracks every construction project from ground break to stabilization.
On budget. On schedule. Presales on track. Debt obligations met.
Goal: Get to the refinance. Achieve 100% financing.
"""
import uuid
from datetime import datetime, date
from typing import Optional, List

GREEN = "green"
YELLOW = "yellow"
RED = "red"
CRITICAL = "critical"


class ProjectMonitor:

    def __init__(self):
        self.projects = {}

    def create_project(self, deal_id: str, data: dict) -> dict:
        project = {
            "deal_id": deal_id,
            "name": data.get("name", "Unnamed Project"),
            "asset_type": data.get("asset_type", "senior_living"),
            "city": data.get("city", ""), "state": data.get("state", ""),
            "gmp_usd": data.get("gmp_usd", 0),
            "soft_costs_usd": data.get("soft_costs_usd", 0),
            "total_budget_usd": data.get("total_budget_usd", 0),
            "contingency_pct": data.get("contingency_pct", 10),
            "scheduled_start": data.get("scheduled_start"),
            "scheduled_completion": data.get("scheduled_completion"),
            "actual_start": data.get("actual_start"),
            "total_units": data.get("total_units", 0),
            "ilu_units": data.get("ilu_units", 0),
            "alu_units": data.get("alu_units", 0),
            "entrance_fee_per_ilu": data.get("entrance_fee_per_ilu", 0),
            "monthly_fee_per_ilu": data.get("monthly_fee_per_ilu", 0),
            "ban_amount_usd": data.get("ban_amount_usd", 0),
            "ban_maturity_date": data.get("ban_maturity_date"),
            "ban_accreted_value_at_maturity": data.get("ban_accreted_value", 0),
            "long_term_bond_target_usd": data.get("long_term_bond_target_usd", 0),
            "target_dscr": data.get("target_dscr", 1.5),
            "has_GMP": data.get("has_GMP", False),
            "has_feasibility": data.get("has_feasibility", False),
            "has_COA": data.get("has_COA", False),
            "long_term_commitment": data.get("long_term_commitment", False),
            "draws": [], "presales": [], "alerts": [],
            "monthly_reports": [],
            "created_at": datetime.utcnow().isoformat(),
        }
        self.projects[deal_id] = project
        return project

    def record_draw(self, deal_id: str, draw: dict) -> dict:
        p = self.projects.get(deal_id)
        if not p:
            return {"error": "Project not found"}
        total_drawn = sum(d["amount_approved_usd"] for d in p["draws"])
        record = {
            "id": f"draw_{len(p['draws'])+1:03d}",
            "draw_number": len(p["draws"]) + 1,
            "period": draw.get("period"),
            "amount_requested_usd": draw.get("amount_usd", 0),
            "amount_approved_usd": draw.get("approved_usd", draw.get("amount_usd", 0)),
            "cumulative_drawn_usd": total_drawn + draw.get("approved_usd", draw.get("amount_usd", 0)),
            "pct_complete": draw.get("pct_complete", 0),
            "lien_waivers": draw.get("lien_waivers", False),
            "architect_certified": draw.get("architect_certified", False),
            "pm_approved": draw.get("pm_approved", False),
            "notes": draw.get("notes", ""),
            "schedule_status": self._schedule_status(p, draw.get("pct_complete", 0)),
            "budget_status": self._budget_status(p, total_drawn + draw.get("approved_usd", draw.get("amount_usd", 0)),
                                                  draw.get("pct_complete", 0)),
            "submitted_at": datetime.utcnow().isoformat(),
        }
        p["draws"].append(record)

        alerts = []
        if record["schedule_status"] in [RED, CRITICAL]:
            a = self._alert(deal_id, "schedule_delay", RED,
                            f"Construction {round(abs(draw.get('pct_complete', 0) - self._expected_pct(p))):,.0f}% behind schedule — refinance risk increasing")
            alerts.append(a)
        if record["budget_status"] in [RED, CRITICAL]:
            a = self._alert(deal_id, "budget_overrun", RED,
                            "Construction costs exceeding GMP — review change orders immediately")
            alerts.append(a)
        record["alerts_generated"] = alerts
        return record

    def _schedule_status(self, p: dict, actual_pct: float) -> str:
        expected = self._expected_pct(p)
        if expected == 0:
            return GREEN
        variance = actual_pct - expected
        if variance >= -5:
            return GREEN
        if variance >= -10:
            return YELLOW
        if variance >= -20:
            return RED
        return CRITICAL

    def _expected_pct(self, p: dict) -> float:
        start = p.get("actual_start") or p.get("scheduled_start")
        end = p.get("scheduled_completion")
        if not start or not end:
            return 0
        try:
            s = datetime.fromisoformat(start)
            e = datetime.fromisoformat(end)
            total = (e - s).days
            elapsed = (datetime.utcnow() - s).days
            return min(100, elapsed / total * 100) if total > 0 else 0
        except Exception:
            return 0

    def _budget_status(self, p: dict, total_drawn: float, pct_complete: float) -> str:
        gmp = p.get("gmp_usd", 0)
        if gmp == 0:
            return GREEN
        expected_spend = gmp * (pct_complete / 100)
        if expected_spend == 0:
            return GREEN
        variance_pct = (total_drawn - expected_spend) / gmp * 100
        if variance_pct <= 5:
            return GREEN
        if variance_pct <= 10:
            return YELLOW
        if variance_pct <= 15:
            return RED
        return CRITICAL

    def record_presale(self, deal_id: str, unit_type: str,
                       unit_number: str, deposit_usd: float,
                       binding: bool = False) -> dict:
        p = self.projects.get(deal_id)
        if not p:
            return {"error": "Not found"}
        sale = {
            "id": f"sale_{uuid.uuid4().hex[:6]}",
            "unit_type": unit_type, "unit_number": unit_number,
            "deposit_usd": deposit_usd, "binding": binding,
            "date": datetime.utcnow().isoformat(),
        }
        p["presales"].append(sale)

        ilu_sold = sum(1 for s in p["presales"] if s["unit_type"] == "ILU")
        total_ilu = max(p.get("ilu_units", 1), 1)
        pct = round(ilu_sold / total_ilu * 100, 1)

        alerts = []
        if pct >= 50 and (ilu_sold - 1) / total_ilu < 0.50:
            alerts.append(self._alert(deal_id, "presales_50",
                                      GREEN, "50% presales achieved — COA application now eligible"))
        if pct >= 70 and (ilu_sold - 1) / total_ilu < 0.70:
            alerts.append(self._alert(deal_id, "presales_70",
                                      GREEN, "70% presales achieved — long-term bond closing eligible"))

        return {**sale, "ilu_presold": ilu_sold, "ilu_total": total_ilu,
                "presale_pct": pct, "milestone_alerts": alerts}

    def get_dashboard(self, deal_id: str) -> dict:
        p = self.projects.get(deal_id)
        if not p:
            return {"error": "Not found"}

        total_drawn = sum(d["amount_approved_usd"] for d in p["draws"])
        gmp = p.get("gmp_usd", 0)
        budget_remaining = gmp - total_drawn
        budget_pct_spent = round(total_drawn / gmp * 100, 1) if gmp else 0

        pct_complete = p["draws"][-1]["pct_complete"] if p["draws"] else 0

        ilu_sold = sum(1 for s in p["presales"] if s["unit_type"] == "ILU")
        total_ilu = max(p.get("ilu_units", 1), 1)
        presale_pct = round(ilu_sold / total_ilu * 100, 1)

        schedule_status = p["draws"][-1]["schedule_status"] if p["draws"] else GREEN
        budget_status = p["draws"][-1]["budget_status"] if p["draws"] else GREEN

        days_to_maturity = None
        if p.get("ban_maturity_date"):
            try:
                m = datetime.fromisoformat(p["ban_maturity_date"])
                days_to_maturity = (m - datetime.utcnow()).days
            except Exception:
                pass

        refinance_ready = (presale_pct >= 70 and p.get("has_GMP") and p.get("has_feasibility"))

        gate = 1
        if p.get("actual_start"):
            gate = 2
        if p.get("has_COA"):
            gate = 3
        if presale_pct >= 50:
            gate = 4
        if p.get("has_feasibility"):
            gate = 5
        if p.get("has_GMP"):
            gate = 6
        if presale_pct >= 70:
            gate = 7
        if p.get("long_term_commitment"):
            gate = 8
        if pct_complete >= 100:
            gate = 9

        return {
            "deal_id": deal_id, "project_name": p["name"],
            "as_of": datetime.utcnow().isoformat(),
            "budget": {
                "gmp_usd": gmp, "total_drawn_usd": round(total_drawn),
                "budget_remaining_usd": round(budget_remaining),
                "pct_spent": budget_pct_spent, "status": budget_status,
                "on_budget": budget_status == GREEN,
            },
            "schedule": {
                "pct_complete": pct_complete,
                "scheduled_completion": p.get("scheduled_completion"),
                "status": schedule_status, "draw_count": len(p["draws"]),
                "on_schedule": schedule_status == GREEN,
            },
            "presales": {
                "ilu_presold": ilu_sold, "ilu_total": total_ilu,
                "presale_pct": presale_pct,
                "gate_50_achieved": presale_pct >= 50,
                "gate_70_achieved": presale_pct >= 70,
                "status": GREEN if presale_pct >= 70 else YELLOW if presale_pct >= 50 else RED,
                "entrance_fee_escrow_usd": round(ilu_sold * p.get("entrance_fee_per_ilu", 0) * 0.10),
            },
            "debt_service": {
                "ban_amount_usd": p.get("ban_amount_usd"),
                "ban_maturity_date": p.get("ban_maturity_date"),
                "days_to_maturity": days_to_maturity,
                "maturity_status": (GREEN if days_to_maturity and days_to_maturity > 365
                                    else YELLOW if days_to_maturity and days_to_maturity > 180
                                    else RED if days_to_maturity else GREEN),
                "refinance_ready": refinance_ready,
                "long_term_bond_target_usd": p.get("long_term_bond_target_usd"),
            },
            "milestone": {
                "current_gate": gate, "total_gates": 10,
                "pct_to_100_financing": gate * 10,
                "refinance_ready": refinance_ready,
            },
            "alerts": [a for a in p.get("alerts", []) if not a.get("acknowledged", False)],
        }

    def _alert(self, deal_id, atype, severity, msg) -> dict:
        a = {"id": f"alert_{uuid.uuid4().hex[:6]}", "deal_id": deal_id,
             "type": atype, "severity": severity, "message": msg,
             "created_at": datetime.utcnow().isoformat(),
             "acknowledged": False}
        if deal_id in self.projects:
            self.projects[deal_id]["alerts"].append(a)
        return a


project_monitor = ProjectMonitor()
