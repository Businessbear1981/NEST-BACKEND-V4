"""
Convergence Engine — Multi-Signal M&A Target Detection.

Watches for 2-3 signals converging on the same entity within a time window.
Single signals = noise. Convergence = a deal.

Runs autonomously. No human input required. Surfaces HEAT events
when signal clusters are detected.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any


# ── Signal Types ──────────────────────────────────────────────────

SIGNAL_TYPES = {
    "llc_formation": {"source": "Secretary of State", "weight": 0.6, "category": "entity"},
    "land_purchase": {"source": "County Recorder", "weight": 0.8, "category": "property"},
    "equity_raise": {"source": "SEC EDGAR Form D", "weight": 0.9, "category": "capital"},
    "8k_filing": {"source": "SEC EDGAR 8-K", "weight": 0.7, "category": "disclosure"},
    "sc13d_filing": {"source": "SEC EDGAR SC 13D", "weight": 0.85, "category": "ownership"},
    "ucc_filing": {"source": "UCC Registry", "weight": 0.65, "category": "debt"},
    "construction_loan_ucc": {"source": "UCC Registry", "weight": 0.8, "category": "construction"},
    "building_permit": {"source": "County Permits", "weight": 0.75, "category": "construction"},
    "surety_bond_filed": {"source": "State Insurance", "weight": 0.7, "category": "construction"},
    "large_wire": {"source": "FinCEN / Banking", "weight": 0.5, "category": "capital"},
    "officer_change": {"source": "Secretary of State", "weight": 0.4, "category": "entity"},
    "parent_acquisition": {"source": "SEC EDGAR", "weight": 0.95, "category": "ownership"},
    "cmbs_maturity": {"source": "EMMA / Trepp", "weight": 0.85, "category": "debt"},
    "tenant_vacancy_spike": {"source": "CoStar / Market", "weight": 0.7, "category": "property"},
    "property_listed": {"source": "CBRE / JLL / LoopNet", "weight": 0.6, "category": "property"},
    "bankruptcy_filing": {"source": "PACER / Court", "weight": 0.9, "category": "distress"},
    "foreclosure_notice": {"source": "County Recorder", "weight": 0.85, "category": "distress"},
    "deed_transfer": {"source": "County Recorder", "weight": 0.7, "category": "property"},
    "tax_lien": {"source": "County Tax", "weight": 0.6, "category": "distress"},
    "merger_announcement": {"source": "SEC / Press", "weight": 0.95, "category": "ownership"},
}


# ── Known Convergence Patterns ────────────────────────────────────
# When these signal combinations appear together, it means something specific.

CONVERGENCE_PATTERNS = [
    {
        "name": "Project Assembly",
        "signals": ["llc_formation", "land_purchase", "equity_raise"],
        "min_match": 2,
        "description": "Entity formed, land acquired, capital being raised. Someone is assembling a project.",
        "deal_type": "bond",
        "urgency": "high",
        "deploy": ["merlin", "lender_scout"],
    },
    {
        "name": "Leveraged Buyout",
        "signals": ["parent_acquisition", "large_wire", "ucc_filing"],
        "min_match": 2,
        "description": "Company acquired with secured debt. LBO in progress.",
        "deal_type": "ma",
        "urgency": "high",
        "deploy": ["merlin", "maxwell"],
    },
    {
        "name": "Capital Raise Expansion",
        "signals": ["8k_filing", "equity_raise", "llc_formation"],
        "min_match": 2,
        "description": "Public disclosure + equity raise + new entity. Company raising capital for expansion.",
        "deal_type": "ma",
        "urgency": "medium",
        "deploy": ["merlin", "sterling"],
    },
    {
        "name": "Ground-Up Development",
        "signals": ["building_permit", "construction_loan_ucc", "surety_bond_filed"],
        "min_match": 2,
        "description": "Permit + construction financing + surety. New development starting.",
        "deal_type": "bond",
        "urgency": "high",
        "deploy": ["merlin", "lender_scout", "surety_scout"],
    },
    {
        "name": "Distressed Asset — Phoenix Candidate",
        "signals": ["cmbs_maturity", "property_listed", "tenant_vacancy_spike"],
        "min_match": 2,
        "description": "Maturing debt + listed + vacancies. Distressed asset — Phoenix acquisition opportunity.",
        "deal_type": "phoenix",
        "urgency": "critical",
        "deploy": ["merlin", "sentinel"],
    },
    {
        "name": "Forced Liquidation",
        "signals": ["bankruptcy_filing", "foreclosure_notice", "property_listed"],
        "min_match": 2,
        "description": "Bankruptcy + foreclosure + listing. Forced sale incoming — deep discount opportunity.",
        "deal_type": "phoenix",
        "urgency": "critical",
        "deploy": ["merlin", "maxwell"],
    },
    {
        "name": "Ownership Change",
        "signals": ["sc13d_filing", "officer_change", "deed_transfer"],
        "min_match": 2,
        "description": "Ownership stake changed + new officers + property transferred. Control is moving.",
        "deal_type": "ma",
        "urgency": "medium",
        "deploy": ["merlin"],
    },
    {
        "name": "Debt Distress",
        "signals": ["tax_lien", "ucc_filing", "tenant_vacancy_spike"],
        "min_match": 2,
        "description": "Tax liens + new debt + vacancies. Entity under financial pressure.",
        "deal_type": "term_lending",
        "urgency": "high",
        "deploy": ["merlin", "sentinel", "lender_scout"],
    },
    {
        "name": "PE Rollup Signal",
        "signals": ["parent_acquisition", "merger_announcement", "equity_raise"],
        "min_match": 2,
        "description": "Acquisition + merger + capital raise. PE firm executing a rollup strategy.",
        "deal_type": "ma",
        "urgency": "high",
        "deploy": ["merlin", "sterling"],
    },
]


def _entity_id(name: str) -> str:
    return hashlib.md5(name.lower().strip().encode()).hexdigest()[:12]


def _ts(offset_days: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


class ConvergenceEngine:
    """
    Watches signal feeds. Detects convergence. Surfaces HEAT events.
    No human input required — runs autonomously.
    """

    def __init__(self) -> None:
        self._signals: list[dict[str, Any]] = []
        self._heat_events: list[dict[str, Any]] = []
        self._seed_demo_signals()
        self._scan_for_convergence()

    def _seed_demo_signals(self) -> None:
        """Generate realistic demo signals that produce convergence events."""
        rng = random.Random(42)

        # Cluster 1: Project Assembly in San Jose
        self._signals.extend([
            {"id": "sig-001", "type": "llc_formation", "entity": "Meridian Development Partners LLC", "location": "San Jose, CA", "date": _ts(12), "details": "New LLC formed in CA — registered agent: Greenberg Traurig LLP", "state": "CA"},
            {"id": "sig-002", "type": "land_purchase", "entity": "Meridian Development Partners LLC", "location": "San Jose, CA", "date": _ts(8), "details": "4.2 acre parcel acquired — 200 Park Ave, San Jose — $18.4M deed recorded", "state": "CA"},
            {"id": "sig-003", "type": "equity_raise", "entity": "Meridian Development Partners LLC", "location": "San Jose, CA", "date": _ts(5), "details": "SEC Form D filed — $42M equity raise — Rule 506(c) — accredited investors", "state": "CA"},
        ])

        # Cluster 2: Distressed Asset in Oakland
        self._signals.extend([
            {"id": "sig-004", "type": "cmbs_maturity", "entity": "1400 Maritime LLC", "location": "Oakland, CA", "date": _ts(30), "details": "CMBS loan $34M maturing — EMMA CUSIP 649346AB2 — no refi filed", "state": "CA"},
            {"id": "sig-005", "type": "tenant_vacancy_spike", "entity": "1400 Maritime LLC", "location": "Oakland, CA", "date": _ts(20), "details": "CoStar vacancy rate jumped 62% → 78% — 3 tenants vacated Q1", "state": "CA"},
            {"id": "sig-006", "type": "property_listed", "entity": "1400 Maritime LLC", "location": "Oakland, CA", "date": _ts(7), "details": "CBRE listing — industrial warehouse — asking $28M (was $42M market)", "state": "CA"},
        ])

        # Cluster 3: LBO in Portland
        self._signals.extend([
            {"id": "sig-007", "type": "parent_acquisition", "entity": "Cascade Holdings Inc", "location": "Portland, OR", "date": _ts(15), "details": "SEC 8-K filed — Cascade acquired by Apex Capital Partners — $56M transaction", "state": "OR"},
            {"id": "sig-008", "type": "ucc_filing", "entity": "Cascade Holdings Inc", "location": "Portland, OR", "date": _ts(10), "details": "UCC-1 filed — $38M secured note — Bank of America as secured party", "state": "OR"},
            {"id": "sig-009", "type": "large_wire", "entity": "Cascade Holdings Inc", "location": "Portland, OR", "date": _ts(9), "details": "Large wire transfer flagged — $38M inbound — BoA origination", "state": "OR"},
        ])

        # Cluster 4: Ground-Up Development in Sacramento
        self._signals.extend([
            {"id": "sig-010", "type": "building_permit", "entity": "Sierra Vista Development Corp", "location": "Sacramento, CA", "date": _ts(18), "details": "Building permit issued — 280-unit mixed-use — 3200 Arden Way — $78M estimated cost", "state": "CA"},
            {"id": "sig-011", "type": "construction_loan_ucc", "entity": "Sierra Vista Development Corp", "location": "Sacramento, CA", "date": _ts(14), "details": "UCC-1 filed — construction loan — $52M — Wells Fargo secured party", "state": "CA"},
            {"id": "sig-012", "type": "surety_bond_filed", "entity": "Sierra Vista Development Corp", "location": "Sacramento, CA", "date": _ts(11), "details": "Performance bond filed — $78M — Hylant Group / Liberty Mutual", "state": "CA"},
        ])

        # Scatter: individual signals (noise — no convergence)
        noise_entities = ["Random Corp A", "XYZ Holdings", "Pacific Ventures", "Metro Properties", "Greenfield LLC", "Summit Partners", "Atlas Investments", "Pinnacle Group"]
        noise_types = list(SIGNAL_TYPES.keys())
        states = ["CA", "TX", "WA", "FL", "OR", "AZ", "NV", "CO"]
        for i in range(20):
            self._signals.append({
                "id": f"sig-n{i:03d}",
                "type": rng.choice(noise_types),
                "entity": rng.choice(noise_entities),
                "location": f"{rng.choice(['Los Angeles', 'Houston', 'Seattle', 'Miami', 'Denver', 'Phoenix'])}, {rng.choice(states)}",
                "date": _ts(rng.randint(1, 60)),
                "details": "Signal detected — single occurrence, no convergence",
                "state": rng.choice(states),
            })

    def _scan_for_convergence(self) -> None:
        """Scan all signals for convergence patterns. Fully autonomous."""
        # Group signals by entity
        entity_signals: dict[str, list[dict]] = {}
        for sig in self._signals:
            eid = _entity_id(sig["entity"])
            entity_signals.setdefault(eid, []).append(sig)

        self._heat_events = []
        for eid, sigs in entity_signals.items():
            if len(sigs) < 2:
                continue

            sig_types = set(s["type"] for s in sigs)
            entity_name = sigs[0]["entity"]
            location = sigs[0]["location"]

            # Check each convergence pattern
            for pattern in CONVERGENCE_PATTERNS:
                matched = sig_types & set(pattern["signals"])
                if len(matched) >= pattern["min_match"]:
                    # Calculate convergence score
                    weights = [SIGNAL_TYPES[st]["weight"] for st in matched]
                    convergence_score = round(sum(weights) / len(pattern["signals"]) * 100, 1)

                    # Time window check
                    dates = [s["date"] for s in sigs if s["type"] in matched]
                    dates.sort()
                    if len(dates) >= 2:
                        first = datetime.strptime(dates[0], "%Y-%m-%dT%H:%M:%SZ")
                        last = datetime.strptime(dates[-1], "%Y-%m-%dT%H:%M:%SZ")
                        window_days = abs((last - first).days)
                    else:
                        window_days = 0

                    self._heat_events.append({
                        "id": f"heat-{eid[:6]}-{pattern['name'][:8].lower().replace(' ', '')}",
                        "entity": entity_name,
                        "location": location,
                        "pattern": pattern["name"],
                        "description": pattern["description"],
                        "deal_type": pattern["deal_type"],
                        "urgency": pattern["urgency"],
                        "matched_signals": list(matched),
                        "signal_count": len(matched),
                        "total_signals_on_entity": len(sigs),
                        "convergence_score": convergence_score,
                        "window_days": window_days,
                        "recommended_agents": pattern["deploy"],
                        "signals": [s for s in sigs if s["type"] in matched],
                        "detected_at": _ts(0),
                    })

        # Sort by convergence score descending
        self._heat_events.sort(key=lambda h: h["convergence_score"], reverse=True)

    # ── Public API ────────────────────────────────────────────────

    def get_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        """All raw signals, most recent first."""
        sorted_sigs = sorted(self._signals, key=lambda s: s["date"], reverse=True)
        return sorted_sigs[:limit]

    def get_heat_events(self) -> list[dict[str, Any]]:
        """All convergence events (HEAT), scored and ranked."""
        return self._heat_events

    def get_heat_event(self, heat_id: str) -> dict[str, Any] | None:
        """Single heat event detail."""
        return next((h for h in self._heat_events if h["id"] == heat_id), None)

    def get_entity_signals(self, entity_name: str) -> list[dict[str, Any]]:
        """All signals for a specific entity."""
        eid = _entity_id(entity_name)
        return [s for s in self._signals if _entity_id(s["entity"]) == eid]

    def get_signal_types(self) -> dict[str, Any]:
        """Available signal types and their metadata."""
        return SIGNAL_TYPES

    def get_patterns(self) -> list[dict[str, Any]]:
        """Known convergence patterns."""
        return CONVERGENCE_PATTERNS

    def stats(self) -> dict[str, Any]:
        """Engine statistics."""
        return {
            "total_signals": len(self._signals),
            "unique_entities": len(set(_entity_id(s["entity"]) for s in self._signals)),
            "heat_events": len(self._heat_events),
            "critical_events": len([h for h in self._heat_events if h["urgency"] == "critical"]),
            "high_events": len([h for h in self._heat_events if h["urgency"] == "high"]),
            "patterns_monitored": len(CONVERGENCE_PATTERNS),
            "signal_types_tracked": len(SIGNAL_TYPES),
        }
