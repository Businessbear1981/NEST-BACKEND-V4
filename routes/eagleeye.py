"""
NEST EagleEye Routes — Business Development & Deal Sourcing.
Pillar 1: Scans UCC filings, title reports, permits, EDGAR, market signals.
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth
from datetime import datetime
import threading
from services.auth import require_auth

eagleeye_bp = Blueprint("eagleeye", __name__)

_signals = []
_scout_runs = []
_lock = threading.Lock()

# Seed some realistic signals
_signals = [
    {
        "id": "sig_1", "type": "ucc_filing", "source": "FL Secretary of State",
        "entity": "Jacaranda Trace Holdings LLC", "amount_usd": 231_000_000,
        "naics": "6232", "state": "FL", "county": "Ventura",
        "detail": "UCC-1 filing — $231M blanket lien, senior living CCRC",
        "score": 92, "status": "hot", "discoveredAt": "2026-05-10T14:22:00Z",
    },
    {
        "id": "sig_2", "type": "permit", "source": "Maricopa County Permits",
        "entity": "Meridian Cove Senior Living LLC", "amount_usd": 145_000_000,
        "naics": "6232", "state": "AZ", "county": "Maricopa",
        "detail": "Building permit issued — 220-unit assisted living, Phase I",
        "score": 78, "status": "warm", "discoveredAt": "2026-05-08T09:15:00Z",
    },
    {
        "id": "sig_3", "type": "edgar_filing", "source": "SEC EDGAR",
        "entity": "Redwood Healthcare REIT", "amount_usd": 89_000_000,
        "naics": "6231", "state": "WA", "county": "King",
        "detail": "8-K filing — acquisition of 3 nursing care facilities",
        "score": 65, "status": "warm", "discoveredAt": "2026-05-07T16:45:00Z",
    },
    {
        "id": "sig_4", "type": "title_transfer", "source": "Orange County Recorder",
        "entity": "Cascadia Development Partners", "amount_usd": 67_000_000,
        "naics": "5311", "state": "CA", "county": "Orange",
        "detail": "Title transfer — 14-acre commercial parcel, zoned mixed-use",
        "score": 55, "status": "review", "discoveredAt": "2026-05-06T11:30:00Z",
    },
]


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


@eagleeye_bp.route("/signals", methods=["GET"])

def list_signals():
    """All discovered deal signals, sorted by score."""
    status_filter = request.args.get("status")
    naics_filter = request.args.get("naics")
    with _lock:
        filtered = _signals[:]
    if status_filter:
        filtered = [s for s in filtered if s["status"] == status_filter]
    if naics_filter:
        filtered = [s for s in filtered if s["naics"] == naics_filter]
    filtered.sort(key=lambda s: s["score"], reverse=True)
    return _ok({
        "signals": filtered,
        "total": len(filtered),
        "hot": sum(1 for s in filtered if s["status"] == "hot"),
        "warm": sum(1 for s in filtered if s["status"] == "warm"),
    })


@eagleeye_bp.route("/signals/<signal_id>", methods=["GET"])

def get_signal(signal_id):
    with _lock:
        sig = next((s for s in _signals if s["id"] == signal_id), None)
    if not sig:
        return _err("Signal not found", 404)
    return _ok(sig)


@eagleeye_bp.route("/signals/<signal_id>/status", methods=["PATCH"])
def update_signal_status(signal_id):
    b = request.get_json() or {}
    new_status = b.get("status")
    valid = ["hot", "warm", "review", "passed", "converted"]
    if new_status not in valid:
        return _err(f"Status must be one of: {valid}")
    with _lock:
        sig = next((s for s in _signals if s["id"] == signal_id), None)
        if not sig:
            return _err("Signal not found", 404)
        sig["status"] = new_status
    return _ok(sig)


@eagleeye_bp.route("/scout", methods=["POST"])
def run_scout():
    """Run AI-powered scout — searches for new deal opportunities."""
    b = request.get_json() or {}
    target_naics = b.get("naics", "6232")
    target_states = b.get("states", ["FL", "TX", "AZ", "CA", "WA"])
    min_size = b.get("min_size_usd", 25_000_000)

    from services.ai_router import plugin_hub
    from services.core import NAICS

    naics_desc = NAICS.get(target_naics, "Unknown")
    prompt = (
        f"You are a bond origination scout. Find 3 realistic deal opportunities "
        f"in {naics_desc} (NAICS {target_naics}) across {', '.join(target_states)}. "
        f"Minimum deal size: ${min_size:,.0f}. "
        f"For each, provide: entity name, city/state, estimated project cost, "
        f"NAICS code, deal type (new development/acquisition/refinance), "
        f"and a 1-sentence rationale. Format as numbered list."
    )

    result = plugin_hub.route("bd_outreach", prompt)

    run = {
        "id": f"scout_{len(_scout_runs)+1}",
        "naics": target_naics,
        "naics_desc": naics_desc,
        "states": target_states,
        "min_size_usd": min_size,
        "ai_results": result.get("content", "") if result.get("success") else "Scout unavailable",
        "tool_used": result.get("tool", "none"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    with _lock:
        _scout_runs.append(run)

    return _ok(run)


@eagleeye_bp.route("/scout/history", methods=["GET"])

def scout_history():
    with _lock:
        return _ok(_scout_runs[::-1])


@eagleeye_bp.route("/convert/<signal_id>", methods=["POST"])
def convert_to_deal(signal_id):
    """Convert a signal into a NEST deal — pushes to Roots."""
    with _lock:
        sig = next((s for s in _signals if s["id"] == signal_id), None)
    if not sig:
        return _err("Signal not found", 404)

    # Create deal stub from signal
    deal_stub = {
        "name": sig["entity"],
        "source": "eagleeye",
        "signal_id": sig["id"],
        "naics": sig["naics"],
        "state": sig["state"],
        "county": sig.get("county", ""),
        "estimated_cost_usd": sig["amount_usd"],
        "status": "intake",
        "eagleeye_score": sig["score"],
        "convertedAt": datetime.utcnow().isoformat(),
    }

    with _lock:
        sig["status"] = "converted"

    return _ok(deal_stub)


@eagleeye_bp.route("/ipo-readiness", methods=["POST"])
def ipo_readiness():
    """Assess IPO readiness for a target company."""
    body = request.get_json() or {}
    from agents.merlin import merlin
    result = merlin.assess_ipo_readiness(body.get("target", {}))
    return _ok(result)


@eagleeye_bp.route("/stats", methods=["GET"])
def stats():
    with _lock:
        total = len(_signals)
        pipeline_usd = sum(s["amount_usd"] for s in _signals if s["status"] in ("hot", "warm"))
        converted = sum(1 for s in _signals if s["status"] == "converted")
    return _ok({
        "total_signals": total,
        "pipeline_usd": pipeline_usd,
        "converted": converted,
        "scout_runs": len(_scout_runs),
    })
