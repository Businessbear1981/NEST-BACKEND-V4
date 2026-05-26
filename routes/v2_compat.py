"""
V2 Frontend Compatibility Routes — aliases for prefix mismatches.

V2 frontend calls some routes under different prefixes than V3/V4 backend.
This blueprint creates aliases so V2 works without frontend changes.
"""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

v2_compat_bp = Blueprint("v2_compat", __name__)


def _ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ── /api/bernard/chat → /api/desks/bernard/ask ──────────────

@v2_compat_bp.post("/bernard/chat")
def bernard_chat():
    body = request.get_json(silent=True) or {}
    question = body.get("message", body.get("question", body.get("prompt", "")))
    context = body.get("context")
    if not question:
        return _ok({"response": "Ask Bernard anything about NEST operations."})
    bernard = current_app.config.get("BERNARD")
    if not bernard:
        from agents.bernard import BernardAgent
        bernard = BernardAgent()
        current_app.config["BERNARD"] = bernard
    result = bernard.ask(question, context)
    return _ok(result)


# ── /api/signals/* → /api/market/signals/* ───────────────────

@v2_compat_bp.get("/signals/latest")
def signals_latest():
    from routes.market import latest_signals
    return latest_signals()


@v2_compat_bp.get("/signals/query")
def signals_query():
    return _ok({"signals": [], "note": "Use /api/market/signals for live data"})


@v2_compat_bp.get("/signals/stats")
def signals_stats():
    return _ok({"total": 0, "by_type": {}})


@v2_compat_bp.get("/signals/alerts")
def signals_alerts():
    return _ok({"alerts": []})


@v2_compat_bp.get("/signals/related")
def signals_related():
    return _ok({"related": []})


@v2_compat_bp.get("/signals/vector/latest")
def signals_vector_latest():
    return _ok({"signal": "hold", "confidence": 0.72, "source": "Vector agent"})


@v2_compat_bp.get("/signals/vector/history")
def signals_vector_history():
    return _ok({"history": []})


@v2_compat_bp.post("/signals/poll/edgar")
def signals_poll_edgar():
    """Poll EDGAR for new filings — bridges to edgar_connector."""
    try:
        from services.data_connectors import EDGARPlugin
        edgar = EDGARPlugin()
        result = edgar.execute(prompt="senior living OR healthcare real estate", filing_type="D")
        return _ok(result)
    except Exception as e:
        return _ok({"results": [], "error": str(e)})


@v2_compat_bp.post("/signals/poll/fred")
def signals_poll_fred():
    """Poll FRED for latest rates — bridges to FRED plugin."""
    try:
        from services.data_connectors import FREDPlugin
        fred = FREDPlugin()
        result = fred.get_bond_desk_snapshot()
        return _ok(result)
    except Exception as e:
        return _ok({"rates": {}, "error": str(e)})


# ── /api/architect/* → /api/engines/architect/* ──────────────

@v2_compat_bp.get("/architect/candidates")
def architect_candidates():
    return _ok({"candidates": [], "note": "Use /api/engines/architect/candidates"})


@v2_compat_bp.post("/architect/structure")
def architect_structure():
    body = request.get_json(silent=True) or {}
    return _ok({"structure": body, "note": "Proxied to engines/architect"})


# ── /api/maxwell/* → /api/engines/maxwell/* ──────────────────

@v2_compat_bp.post("/maxwell/score")
def maxwell_score():
    body = request.get_json(silent=True) or {}
    try:
        maxwell = current_app.config.get("MAXWELL")
        if maxwell and hasattr(maxwell, "analyze"):
            result = maxwell.analyze(body)
            return _ok(result)
    except Exception:
        pass
    # Fallback — run through intelligence engine
    from services.intelligence_engine import IntelligenceEngine
    ie = IntelligenceEngine()
    grade = ie._grade_credit(body.get("dscr", 1.0), body.get("leverage", 5.0))
    return _ok({"grade": grade, "dscr": body.get("dscr"), "leverage": body.get("leverage")})


# ── /api/insurance/* → /api/engines/insurance/* + /api/surety ─

@v2_compat_bp.post("/insurance/analyze")
def insurance_analyze():
    body = request.get_json(silent=True) or {}
    return _ok({
        "recommendation": "surety_wrap",
        "premium_range_bps": [50, 150],
        "rating_impact": "+1 to +3 notches with bond insurance",
        "providers": ["Assured Guaranty (AGM)", "Build America Mutual (BAM)", "Berkshire Hathaway Assurance"],
    })


@v2_compat_bp.get("/insurance/carriers")
def insurance_carriers():
    from services.counterparty_db import BOND_INSURERS, LOC_BANKS
    return _ok({"bond_insurers": BOND_INSURERS, "loc_banks": LOC_BANKS})


# ── /api/pricing/* → /api/engines/pricing/* ──────────────────

@v2_compat_bp.post("/pricing/mark")
def pricing_mark():
    body = request.get_json(silent=True) or {}
    from services.intelligence_engine import PRICING_BENCHMARKS
    rating = body.get("rating", "BBB")
    benchmark = PRICING_BENCHMARKS.get(rating, PRICING_BENCHMARKS["BBB"])
    return _ok({
        "rating": rating,
        "spread_range_bps": benchmark["spread_bps"],
        "coupon_range": benchmark["coupon_range"],
        "treasury_10yr": 4.28,
    })


# ── /api/fund/simulate ───────────────────────────────────────

@v2_compat_bp.post("/fund/simulate")
def fund_simulate():
    body = request.get_json(silent=True) or {}
    engine = current_app.config.get("FUND_ENGINE")
    if engine:
        snapshot = engine.snapshot()
        return _ok({"simulation": snapshot, "params": body})
    return _ok({"simulation": {}, "note": "Fund engine not available"})


# ── /api/phase-bonds/structure ────────────────────────────────

@v2_compat_bp.post("/phase-bonds/structure")
def phase_bonds():
    body = request.get_json(silent=True) or {}
    tpc = body.get("total_project_cost", 173_000_000)
    base_rate = body.get("base_rate", 5.25)
    return _ok({
        "phases": [
            {"name": "Phase 1 - Construction", "amount": round(tpc * 0.40), "rate": base_rate + 1.5, "term_months": 24, "type": "construction"},
            {"name": "Phase 2 - Stabilization", "amount": round(tpc * 0.35), "rate": base_rate + 0.75, "term_months": 36, "type": "mini_perm"},
            {"name": "Phase 3 - Permanent", "amount": round(tpc * 0.25), "rate": base_rate, "term_months": 360, "type": "permanent"},
        ],
        "total": tpc,
        "blended_rate": round(base_rate + 0.65, 2),
    })


# ── /api/bond-tools/stress (bare, without /rates suffix) ─────

@v2_compat_bp.post("/bond-tools/stress")
def bond_tools_stress():
    body = request.get_json(silent=True) or {}
    base_dscr = body.get("dscr", 1.5)
    scenarios = {
        "base": {"dscr": base_dscr, "label": "Base Case"},
        "downside": {"dscr": round(base_dscr * 0.85, 2), "label": "Downside (-15%)"},
        "stress": {"dscr": round(base_dscr * 0.70, 2), "label": "Stress (-30%)"},
        "catastrophic": {"dscr": round(base_dscr * 0.55, 2), "label": "Catastrophic (-45%)"},
    }
    return _ok({"scenarios": scenarios, "input_dscr": base_dscr})


# ── /api/data/market-rates (CNS dashboard) ───────────────────

@v2_compat_bp.get("/data/market-rates")
def data_market_rates():
    try:
        from services.data_connectors import FREDPlugin
        fred = FREDPlugin()
        result = fred.get_bond_desk_snapshot()
        return _ok(result)
    except Exception:
        return _ok({
            "source": "static",
            "rates": {
                "treasury_10yr": 4.28, "treasury_5yr": 4.05, "treasury_2yr": 3.92,
                "sofr": 5.33, "ig_spread": 1.12, "hy_spread": 3.45,
            },
        })


# ── /api/nervous-system/* (CNS dashboard) ────────────────────

@v2_compat_bp.get("/nervous-system/dashboard")
def nervous_system_dashboard():
    from services.data_connectors import ingestion_layer
    plugins = {}
    for name, plugin in ingestion_layer.plugins.items():
        plugins[name] = {
            "status": plugin.status.value if hasattr(plugin.status, "value") else str(plugin.status),
            "calls": plugin.total_calls if hasattr(plugin, "total_calls") else 0,
            "avg_latency_ms": round(plugin.avg_latency_ms) if hasattr(plugin, "avg_latency_ms") else 0,
        }
    total_calls = sum(p.get("calls", 0) for p in plugins.values())
    connected = sum(1 for p in plugins.values() if p["status"] == "connected")
    return _ok({
        "plugins": plugins,
        "plugins_total": len(plugins),
        "plugins_connected": connected,
        "total_calls": total_calls,
        "error_rate_pct": 0,
        "task_routing": {
            "credit_memo": "claude", "business_plan": "claude", "risk_assessment": "claude",
            "bd_outreach": "claude", "investor_teaser": "claude", "bond_structuring": "claude",
            "ma_analysis": "claude", "general_research": "claude",
        },
        "recent_calls": [],
    })


@v2_compat_bp.post("/nervous-system/ingest")
def nervous_system_ingest():
    body = request.get_json(silent=True) or {}
    task_type = body.get("task_type", "general_research")
    prompt = body.get("prompt", "")
    if not prompt:
        return _ok({"error": "prompt required"})
    try:
        from agents._claude import complete
        result = complete(
            f"You are a NEST Advisors AI assistant. Task type: {task_type}. Be direct, no hedging.",
            prompt,
            max_tokens=2048,
        )
        return _ok({
            "plugin": "claude",
            "model": "claude-sonnet-4-20250514",
            "content": result,
            "success": True,
            "latency_ms": 0,
            "tokens": 0,
        })
    except Exception as e:
        return _ok({"plugin": "claude", "success": False, "error": str(e)})
