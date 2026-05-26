"""
NEST Phoenix Engine — Distressed CRE Acquisition & Rehabilitation.
Mock data for problem assets, environmental brownfields, underwriting,
bridge timelines, sourcing radar, and warchest portfolio tracking.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any


def _ts(offset_days: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:04d}"


# ── Deal pipeline ─────────────────────────────────────────────────────

PHOENIX_DEALS = [
    {
        "id": "phx-1",
        "name": "San Jose Office Tower",
        "address": "200 Park Ave, San Jose, CA 95113",
        "asset_type": "Office",
        "market_value": 100_000_000,
        "purchase_price": 68_000_000,
        "discount_pct": 32.0,
        "ltv_at_acquisition": 68.0,
        "instant_equity": 32_000_000,
        "track": "rent_shortfall",
        "current_noi": 4_200_000,
        "target_noi": 7_800_000,
        "current_occupancy": 62,
        "target_occupancy": 92,
        "current_dscr": 0.72,
        "stabilized_dscr": 1.41,
        "no_pi_months": 30,
        "source": "CBRE",
        "source_contact": "Josh Edwards",
        "stage": "underwriting",
        "created_at": _ts(14),
    },
    {
        "id": "phx-2",
        "name": "Oakland Industrial Warehouse",
        "address": "1400 Maritime St, Oakland, CA 94607",
        "asset_type": "Industrial",
        "market_value": 42_000_000,
        "purchase_price": 28_000_000,
        "discount_pct": 33.3,
        "ltv_at_acquisition": 66.7,
        "instant_equity": 14_000_000,
        "track": "environmental",
        "current_noi": 0,
        "target_noi": 3_400_000,
        "current_occupancy": 0,
        "target_occupancy": 85,
        "current_dscr": 0,
        "stabilized_dscr": 1.55,
        "no_pi_months": 48,
        "remediation_cost": 6_800_000,
        "phase_status": "Phase II",
        "contamination": "Petroleum hydrocarbons",
        "source": "EPA Brownfield Registry",
        "source_contact": "CA DTSC",
        "stage": "loi",
        "created_at": _ts(28),
    },
    {
        "id": "phx-3",
        "name": "Sacramento Retail Center",
        "address": "3200 Arden Way, Sacramento, CA 95825",
        "asset_type": "Retail",
        "market_value": 31_000_000,
        "purchase_price": 22_000_000,
        "discount_pct": 29.0,
        "ltv_at_acquisition": 71.0,
        "instant_equity": 9_000_000,
        "track": "rent_shortfall",
        "current_noi": 1_800_000,
        "target_noi": 2_900_000,
        "current_occupancy": 54,
        "target_occupancy": 88,
        "current_dscr": 0.82,
        "stabilized_dscr": 1.32,
        "no_pi_months": 24,
        "source": "JLL",
        "source_contact": "Marcus Chen",
        "stage": "bond_structuring",
        "created_at": _ts(45),
    },
    {
        "id": "phx-4",
        "name": "Portland Mixed-Use Complex",
        "address": "800 NW 6th Ave, Portland, OR 97209",
        "asset_type": "Mixed-Use",
        "market_value": 56_000_000,
        "purchase_price": 38_000_000,
        "discount_pct": 32.1,
        "ltv_at_acquisition": 67.9,
        "instant_equity": 18_000_000,
        "track": "both",
        "current_noi": 2_100_000,
        "target_noi": 4_600_000,
        "current_occupancy": 48,
        "target_occupancy": 90,
        "current_dscr": 0.65,
        "stabilized_dscr": 1.38,
        "no_pi_months": 36,
        "remediation_cost": 3_200_000,
        "phase_status": "Phase I",
        "contamination": "Asbestos / lead paint",
        "source": "Bank OREO",
        "source_contact": "Wells Fargo RE",
        "stage": "due_diligence",
        "created_at": _ts(21),
    },
    {
        "id": "phx-5",
        "name": "Seattle Industrial Park",
        "address": "5600 E Marginal Way S, Seattle, WA 98134",
        "asset_type": "Industrial",
        "market_value": 88_000_000,
        "purchase_price": 61_000_000,
        "discount_pct": 30.7,
        "ltv_at_acquisition": 69.3,
        "instant_equity": 27_000_000,
        "track": "environmental",
        "current_noi": 5_200_000,
        "target_noi": 7_100_000,
        "current_occupancy": 71,
        "target_occupancy": 95,
        "current_dscr": 1.08,
        "stabilized_dscr": 1.62,
        "no_pi_months": 36,
        "remediation_cost": 4_500_000,
        "phase_status": "Phase III Complete",
        "contamination": "Heavy metals (remediated)",
        "source": "Cushman & Wakefield",
        "source_contact": "Sarah Park",
        "stage": "closed",
        "created_at": _ts(180),
    },
]

PIPELINE_STAGES = ["sourced", "underwriting", "loi", "due_diligence", "bond_structuring", "closed"]

# ── Sourcing radar ────────────────────────────────────────────────────

RADAR_FEED = [
    {"id": "rdr-1", "address": "450 S Orange Ave, Orlando, FL 32801", "type": "Office", "value": 78_000_000, "asking": 52_000_000, "discount": 33, "track": "rent_shortfall", "score": 87, "msa": "Orlando-Kissimmee"},
    {"id": "rdr-2", "address": "1200 Smith St, Houston, TX 77002", "type": "Office", "value": 145_000_000, "asking": 98_000_000, "discount": 32, "track": "rent_shortfall", "score": 82, "msa": "Houston-The Woodlands"},
    {"id": "rdr-3", "address": "3400 Industrial Blvd, Austin, TX 78744", "type": "Industrial", "value": 34_000_000, "asking": 18_000_000, "discount": 47, "track": "environmental", "score": 91, "msa": "Austin-Round Rock"},
    {"id": "rdr-4", "address": "900 Market St, San Francisco, CA 94102", "type": "Retail", "value": 62_000_000, "asking": 38_000_000, "discount": 39, "track": "rent_shortfall", "score": 78, "msa": "San Francisco-Oakland"},
    {"id": "rdr-5", "address": "2100 NW Front Ave, Portland, OR 97209", "type": "Industrial", "value": 28_000_000, "asking": 14_000_000, "discount": 50, "track": "environmental", "score": 94, "msa": "Portland-Vancouver"},
    {"id": "rdr-6", "address": "5500 Wilshire Blvd, Los Angeles, CA 90036", "type": "Office", "value": 120_000_000, "asking": 84_000_000, "discount": 30, "track": "rent_shortfall", "score": 75, "msa": "Los Angeles-Long Beach"},
    {"id": "rdr-7", "address": "800 Pike St, Seattle, WA 98101", "type": "Mixed-Use", "value": 55_000_000, "asking": 33_000_000, "discount": 40, "track": "both", "score": 88, "msa": "Seattle-Tacoma"},
    {"id": "rdr-8", "address": "1500 K St NW, Washington, DC 20005", "type": "Office", "value": 92_000_000, "asking": 64_000_000, "discount": 30, "track": "rent_shortfall", "score": 72, "msa": "Washington-Arlington"},
    {"id": "rdr-9", "address": "200 E Broward Blvd, Fort Lauderdale, FL 33301", "type": "Office", "value": 48_000_000, "asking": 29_000_000, "discount": 40, "track": "rent_shortfall", "score": 85, "msa": "Miami-Fort Lauderdale"},
    {"id": "rdr-10", "address": "4200 E Commerce St, San Antonio, TX 78220", "type": "Industrial", "value": 22_000_000, "asking": 11_000_000, "discount": 50, "track": "environmental", "score": 90, "msa": "San Antonio-New Braunfels"},
    {"id": "rdr-11", "address": "700 E Grand Ave, Chicago, IL 60611", "type": "Mixed-Use", "value": 85_000_000, "asking": 55_000_000, "discount": 35, "track": "both", "score": 80, "msa": "Chicago-Naperville"},
    {"id": "rdr-12", "address": "300 Peachtree St NE, Atlanta, GA 30308", "type": "Office", "value": 67_000_000, "asking": 42_000_000, "discount": 37, "track": "rent_shortfall", "score": 83, "msa": "Atlanta-Sandy Springs"},
]


class PhoenixEngine:
    """Mock data engine for Phoenix distressed CRE acquisition module."""

    def __init__(self) -> None:
        self._deals = {d["id"]: dict(d) for d in PHOENIX_DEALS}

    def list_deals(self) -> list[dict[str, Any]]:
        return list(self._deals.values())

    def get_deal(self, deal_id: str) -> dict[str, Any] | None:
        return self._deals.get(deal_id)

    def create_deal(self, data: dict[str, Any]) -> dict[str, Any]:
        new_id = f"phx-{len(self._deals) + 1}"
        deal = {"id": new_id, "stage": "sourced", "created_at": _ts(0), **data}
        self._deals[new_id] = deal
        return deal

    def update_deal(self, deal_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        deal = self._deals.get(deal_id)
        if deal:
            deal.update(data)
        return deal

    def underwriting(self, deal_id: str) -> dict[str, Any] | None:
        deal = self._deals.get(deal_id)
        if not deal:
            return None
        mv = deal["market_value"]
        pp = deal["purchase_price"]
        equity = mv - pp
        ltv = (pp / mv) * 100
        stabilized_value = deal.get("target_noi", 0) / 0.065 if deal.get("target_noi") else mv
        exit_equity = stabilized_value - pp
        bond_size = pp
        ltv_grade = "green" if ltv < 65 else "amber" if ltv < 75 else "red"
        dscr_grade = "green" if deal.get("stabilized_dscr", 0) > 1.25 else "amber" if deal.get("stabilized_dscr", 0) > 1.0 else "red"

        result = {
            "deal_id": deal_id,
            "discount_to_equity": {
                "market_value": mv,
                "purchase_price": pp,
                "instant_equity": equity,
                "discount_pct": round((equity / mv) * 100, 1),
                "ltv_at_acquisition": round(ltv, 1),
                "ltv_grade": ltv_grade,
            },
            "stabilization_plan": {
                "current_noi": deal.get("current_noi", 0),
                "target_noi": deal.get("target_noi", 0),
                "current_occupancy": deal.get("current_occupancy", 0),
                "target_occupancy": deal.get("target_occupancy", 0),
                "no_pi_months": deal.get("no_pi_months", 0),
                "ti_budget": round(mv * 0.008, 2),
                "lease_up_months": 18,
            },
            "bond_feasibility": {
                "recommended_bond_size": bond_size,
                "coupon_range": "6.5% - 7.5%",
                "term_years": 3,
                "no_pi_window_months": deal.get("no_pi_months", 0),
                "stabilized_dscr": deal.get("stabilized_dscr", 0),
                "dscr_grade": dscr_grade,
                "feasible": ltv < 75 and deal.get("stabilized_dscr", 0) > 1.25,
            },
            "exit_modeling": {
                "stabilized_value": round(stabilized_value, 2),
                "exit_equity": round(exit_equity, 2),
                "cap_rate": 6.5,
                "refi_ltv": round((bond_size / stabilized_value) * 100, 1),
                "projected_irr": round(((exit_equity / pp) ** (1 / 3) - 1) * 100, 1),
            },
        }

        if deal.get("track") in ("environmental", "both"):
            result["remediation_plan"] = {
                "contamination_type": deal.get("contamination", "Unknown"),
                "phase_status": deal.get("phase_status", "Phase I"),
                "estimated_cost": deal.get("remediation_cost", 0),
                "timeline_months": deal.get("no_pi_months", 36),
                "post_cleanup_value": round(stabilized_value * 1.15, 2),
                "indemnity_required": True,
            }
        return result

    def timeline(self, deal_id: str) -> dict[str, Any] | None:
        deal = self._deals.get(deal_id)
        if not deal:
            return None
        stage_idx = PIPELINE_STAGES.index(deal["stage"]) if deal["stage"] in PIPELINE_STAGES else 0
        milestones = [
            {"id": "ms-1", "name": "LOI Executed", "target_day": 5, "status": "complete" if stage_idx >= 2 else "pending"},
            {"id": "ms-2", "name": "Due Diligence", "target_day": 15, "status": "complete" if stage_idx >= 3 else "in_progress" if stage_idx == 3 else "pending"},
            {"id": "ms-3", "name": "Appraisal Ordered", "target_day": 20, "status": "complete" if stage_idx >= 3 else "pending"},
            {"id": "ms-4", "name": "Environmental Phase I", "target_day": 25, "status": "complete" if stage_idx >= 3 else "pending"},
            {"id": "ms-5", "name": "Rating Submission", "target_day": 35, "status": "complete" if stage_idx >= 4 else "pending"},
            {"id": "ms-6", "name": "Bond Placement", "target_day": 50, "status": "complete" if stage_idx >= 4 else "pending"},
            {"id": "ms-7", "name": "Bond Close", "target_day": 60, "status": "complete" if stage_idx >= 5 else "pending"},
        ]
        days_elapsed = min(60, stage_idx * 12)
        return {
            "deal_id": deal_id,
            "total_days": 60,
            "days_elapsed": days_elapsed,
            "days_remaining": 60 - days_elapsed,
            "current_stage": deal["stage"],
            "milestones": milestones,
            "bridge_capital_deployed": round(deal["purchase_price"] * 0.05, 2),
        }

    def radar_feed(self) -> list[dict[str, Any]]:
        return RADAR_FEED

    def radar_scores(self) -> list[dict[str, Any]]:
        scored = []
        for r in RADAR_FEED:
            scored.append({
                **r,
                "score_breakdown": {
                    "discount_depth": min(100, int(r["discount"] * 2.5)),
                    "market_strength": random.Random(hash(r["id"])).randint(60, 95),
                    "bond_feasibility": random.Random(hash(r["id"]) + 1).randint(65, 98),
                    "complexity": 100 - random.Random(hash(r["id"]) + 2).randint(10, 40) if r["track"] == "environmental" else 85,
                    "community_impact": random.Random(hash(r["id"]) + 3).randint(60, 95),
                },
            })
        return scored

    def warchest(self) -> dict[str, Any]:
        return {
            "active_stabilization": [
                {
                    "deal_id": "phx-5",
                    "name": "Seattle Industrial Park",
                    "acquisition_price": 61_000_000,
                    "current_estimated_value": 82_000_000,
                    "occupancy_pct": 71,
                    "cash_accumulated": 4_800_000,
                    "months_to_maturity": 14,
                    "status": "stabilizing",
                },
                {
                    "deal_id": "phx-3",
                    "name": "Sacramento Retail Center",
                    "acquisition_price": 22_000_000,
                    "current_estimated_value": 28_000_000,
                    "occupancy_pct": 68,
                    "cash_accumulated": 1_200_000,
                    "months_to_maturity": 22,
                    "status": "stabilizing",
                },
            ],
            "completed": [
                {
                    "deal_id": "phx-exit-1",
                    "name": "Tacoma Distribution Hub",
                    "acquisition_price": 45_000_000,
                    "stabilized_noi": 4_100_000,
                    "current_dscr": 1.48,
                    "equity_position": 22_000_000,
                    "status": "refi_ready",
                },
            ],
            "exited": [
                {
                    "deal_id": "phx-exit-2",
                    "name": "Bellevue Tech Campus",
                    "acquisition_price": 61_000_000,
                    "exit_price": 94_000_000,
                    "realized_gain": 33_000_000,
                    "hold_months": 28,
                    "irr": 22.4,
                    "multiple": 1.54,
                },
            ],
        }

    def warchest_economics(self) -> dict[str, Any]:
        wc = self.warchest()
        total_acquired = sum(a["acquisition_price"] for a in wc["active_stabilization"])
        total_acquired += sum(a["acquisition_price"] for a in wc["completed"])
        total_acquired += sum(a["acquisition_price"] for a in wc["exited"])
        total_equity = sum(a["current_estimated_value"] - a["acquisition_price"] for a in wc["active_stabilization"])
        total_equity += sum(a.get("equity_position", 0) for a in wc["completed"])
        total_equity += sum(a.get("realized_gain", 0) for a in wc["exited"])
        total_cash = sum(a.get("cash_accumulated", 0) for a in wc["active_stabilization"])
        return {
            "total_assets": len(wc["active_stabilization"]) + len(wc["completed"]) + len(wc["exited"]),
            "total_acquired": total_acquired,
            "total_equity_created": total_equity,
            "total_cash_accumulated": total_cash,
            "total_exits_realized": sum(a.get("realized_gain", 0) for a in wc["exited"]),
            "portfolio_nav": total_acquired + total_equity,
            "avg_discount": 31.8,
            "avg_hold_months": 28,
        }

    def bond_handoff(self, deal_id: str) -> dict[str, Any] | None:
        deal = self._deals.get(deal_id)
        if not deal:
            return None
        uw = self.underwriting(deal_id)
        return {
            "deal_id": deal_id,
            "bond_desk_payload": {
                "name": f"Phoenix — {deal['name']}",
                "issuer": "NEST Advisors (Phoenix Fund)",
                "amount": deal["purchase_price"],
                "asset_type": deal["asset_type"],
                "address": deal["address"],
                "ltv": uw["discount_to_equity"]["ltv_at_acquisition"],
                "target_dscr": deal.get("stabilized_dscr", 0),
                "term_years": 3,
                "no_pi_months": deal.get("no_pi_months", 0),
                "coupon_range": "6.5% - 7.5%",
                "source": "Phoenix Acquisition",
            },
            "ready": uw["bond_feasibility"]["feasible"],
        }
