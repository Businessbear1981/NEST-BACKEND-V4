"""Market signals routes — ingest data, Vector scoring."""
import threading
from flask import Blueprint, jsonify, request
from datetime import datetime
from services.auth import require_auth

market_bp = Blueprint("market", __name__)

_lock = threading.RLock()
_signals = []  # list of signal snapshots


def _ts():
    return datetime.utcnow().isoformat()


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": _ts()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg, "timestamp": _ts()}), code


# Default market state
DEFAULT_SIGNALS = {
    "treasury_10yr_pct": 4.25,
    "treasury_10yr_change_bps": -5,
    "sofr_pct": 4.30,
    "credit_spread_ig_bps": 125,
    "credit_spread_hy_bps": 375,
    "tlt_price": 92.50,
    "vix": 18.5,
    "refi_market_access": "open_favorable",
}


@market_bp.route("/signals", methods=["POST"])
def ingest_signals():
    body = request.get_json() or {}
    signals = body.get("signals", DEFAULT_SIGNALS)

    # Simple Vector score computation (placeholder until Vector agent built)
    score = _compute_vector_score(signals)
    recommendation = _vector_recommendation(score)

    entry = {
        "id": len(_signals) + 1,
        "captured_at": _ts(),
        "signals": signals,
        "vector_score": score,
        "vector_recommendation": recommendation,
        "apex_short_active": False,
        "apex_position": None,
    }

    with _lock:
        _signals.append(entry)
        if len(_signals) > 1000:
            _signals.pop(0)

    return _ok(entry, 201)


@market_bp.route("/signals/latest", methods=["GET"])
def latest_signals():
    with _lock:
        if _signals:
            return _ok(_signals[-1])
    # Try live FRED rates before falling back to hardcoded defaults
    signals_to_use = dict(DEFAULT_SIGNALS)
    fred = _get_fred_plugin()
    if fred:
        try:
            snap = fred.get_bond_desk_snapshot()
            if snap.get("success"):
                r = snap["rates"]
                signals_to_use["treasury_10yr_pct"] = r.get("treasury_10yr", 4.25)
                signals_to_use["sofr_pct"] = r.get("sofr", 4.30)
                signals_to_use["credit_spread_ig_bps"] = round(r.get("ig_spread", 1.25) * 100)
                signals_to_use["credit_spread_hy_bps"] = round(r.get("hy_spread", 3.75) * 100)
        except Exception:
            pass
    score = _compute_vector_score(signals_to_use)
    return _ok({
        "captured_at": _ts(),
        "signals": signals_to_use,
        "vector_score": score,
        "vector_recommendation": _vector_recommendation(score),
        "apex_short_active": False,
        "apex_position": None,
    })


def _compute_vector_score(signals: dict) -> int:
    """Simplified Vector scoring — 0-100 composite."""
    score = 50  # neutral start

    # Treasury change: negative = favorable for calls
    t_change = signals.get("treasury_10yr_change_bps", 0)
    if t_change < -25:
        score += 20
    elif t_change < -10:
        score += 10
    elif t_change > 25:
        score -= 15
    elif t_change > 10:
        score -= 8

    # VIX: low = stable
    vix = signals.get("vix", 20)
    if vix < 15:
        score += 10
    elif vix > 25:
        score -= 10
    elif vix > 35:
        score -= 20

    # Credit spreads: tighter = better
    ig_spread = signals.get("credit_spread_ig_bps", 150)
    if ig_spread < 100:
        score += 10
    elif ig_spread > 200:
        score -= 10

    # Market access
    access = signals.get("refi_market_access", "open_neutral")
    if access == "open_favorable":
        score += 10
    elif access == "restricted":
        score -= 15
    elif access == "closed":
        score -= 25

    return max(0, min(100, score))


def _vector_recommendation(score: int) -> str:
    if score >= 85:
        return "execute_call"
    elif score >= 70:
        return "call_eligible"
    elif score >= 50:
        return "monitor"
    elif score >= 30:
        return "hold"
    else:
        return "put_alert"


# ── Live FRED Rates ────────────────────────────────────────────

def _get_fred_plugin():
    try:
        from services.data_connectors import FREDPlugin
        return FREDPlugin()
    except Exception:
        return None


@market_bp.route("/rates/live", methods=["GET"])
def live_rates():
    """Bond Desk live rate snapshot from FRED."""
    fred = _get_fred_plugin()
    if not fred:
        return _err("FRED plugin unavailable", 503)
    snapshot = fred.get_bond_desk_snapshot()
    return _ok(snapshot)


@market_bp.route("/rates/yield-curve", methods=["GET"])
def yield_curve():
    """Full Treasury yield curve."""
    fred = _get_fred_plugin()
    if not fred:
        return _err("FRED plugin unavailable", 503)
    curve = fred.get_yield_curve()
    return _ok(curve)


@market_bp.route("/rates/snapshot", methods=["GET"])
def market_snapshot():
    """Quick market snapshot — key rates for dashboards."""
    fred = _get_fred_plugin()
    if not fred:
        return _err("FRED plugin unavailable", 503)
    snap = fred.get_market_snapshot()
    return _ok(snap)
