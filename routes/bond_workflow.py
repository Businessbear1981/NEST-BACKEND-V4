"""
NEST Bond Workflow Routes — Master orchestration for the BondCommandCenter.
Tracks deal readiness across all 4 pillars (EagleEye, Roots, Bond Desk, Hawkeye).
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth
from datetime import datetime
import threading
from services.auth import require_auth

bond_workflow_bp = Blueprint("bond_workflow", __name__)

_workflows = {}
_lock = threading.Lock()


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _get_or_create_workflow(deal_id: str) -> dict:
    with _lock:
        if deal_id not in _workflows:
            # Try to load real deal data from Supabase
            deal = None
            try:
                from services.database import db
                if db and db.configured:
                    rows = db.select("deals", {"id": f"eq.{deal_id}"})
                    if rows:
                        deal = rows[0]
            except Exception:
                pass

            if deal:
                readiness = deal.get("readiness_score", 0)
                dscr = float(deal.get("dscr", 0))
                ltv = float(deal.get("ltv", 0))
                bond_face = float(deal.get("bond_face", 0))
                checklist = deal.get("checklist", [])
                if isinstance(checklist, str):
                    import json
                    try: checklist = json.loads(checklist)
                    except: checklist = []
                if isinstance(checklist, dict):
                    checklist = [{"label": k, "done": v} for k, v in checklist.items()]

                # Score pillars from real data
                eagle_score = min(100, 40 + (10 if bond_face > 50_000_000 else 0))
                roots_score = readiness
                bond_score = min(100, int(dscr * 30) + (20 if ltv < 70 else 0))
                hawk_score = min(100, 20 + (30 if dscr > 1.5 else 0))

                phase = "structuring" if readiness > 60 else "readiness" if readiness > 30 else "sourcing"
                overall = int((eagle_score + roots_score + bond_score + hawk_score) / 4)

                _workflows[deal_id] = {
                    "dealId": deal_id,
                    "dealName": deal.get("name", ""),
                    "phase": phase,
                    "overallReadinessScore": overall,
                    "pillarScores": {
                        "eagleeye": eagle_score,
                        "roots": roots_score,
                        "bondDesk": bond_score,
                        "hawkeye": hawk_score,
                    },
                    "dealMetrics": {
                        "bondFace": bond_face,
                        "dscr": dscr,
                        "ltv": ltv,
                        "state": deal.get("state"),
                        "market": deal.get("market"),
                        "aeEconomics": float(deal.get("ae_economics", 0)),
                    },
                    "capitalStack": deal.get("capital_stack", []),
                    "stressScenarios": deal.get("stress_scenarios", []),
                    "sourcesUses": deal.get("sources_uses", []),
                    "checklist": checklist,
                    "events": [],
                    "aiAssessment": f"Deal {deal.get('name','')} — ${bond_face/1e6:.0f}M {deal.get('state','')} | DSCR {dscr}x | LTV {ltv}% | Readiness {readiness}%",
                    "createdAt": deal.get("created_at", datetime.utcnow().isoformat()),
                    "updatedAt": deal.get("updated_at", datetime.utcnow().isoformat()),
                }
            else:
                _workflows[deal_id] = {
                    "dealId": deal_id,
                    "phase": "sourcing",
                    "overallReadinessScore": 0,
                    "pillarScores": {"eagleeye": 0, "roots": 0, "bondDesk": 0, "hawkeye": 0},
                    "checklist": [],
                    "events": [],
                    "createdAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat(),
                }
        return _workflows[deal_id]


@bond_workflow_bp.route("/deal/<deal_id>", methods=["GET"])

def get_by_deal(deal_id):
    return _ok(_get_or_create_workflow(deal_id))


@bond_workflow_bp.route("/deal/<deal_id>/run-evaluation", methods=["POST"])
@require_auth()
def run_full_ai_evaluation(deal_id):
    """Run full AI evaluation across all pillars — updates readiness score."""
    wf = _get_or_create_workflow(deal_id)

    # Score each pillar based on available data
    from services.ai_router import plugin_hub

    # EagleEye: sourcing completeness
    eagleeye_score = min(100, len(wf.get("events", [])) * 15 + 25)

    # Roots: document readiness
    checklist = wf.get("checklist", [])
    completed = sum(1 for c in checklist if c.get("completed"))
    roots_score = int(completed / max(len(checklist), 1) * 100) if checklist else 30

    # Bond Desk: structuring readiness
    bond_score = 40 if wf.get("phase") in ("structuring", "placed") else 20

    # Hawkeye: placement progress
    hawkeye_score = 15

    # AI enhancement — ask Claude for a qualitative assessment
    try:
        result = plugin_hub.route(
            "risk_assessment",
            f"Evaluate bond readiness for deal {deal_id}. "
            f"EagleEye sourcing: {eagleeye_score}/100, "
            f"Roots docs: {roots_score}/100, "
            f"Structuring: {bond_score}/100, "
            f"Placement: {hawkeye_score}/100. "
            f"Give a 2-sentence institutional assessment.",
        )
        ai_note = result.get("content", "") if result.get("success") else ""
    except Exception:
        ai_note = ""

    overall = int(eagleeye_score * 0.20 + roots_score * 0.35 +
                  bond_score * 0.30 + hawkeye_score * 0.15)

    with _lock:
        wf["pillarScores"] = {
            "eagleeye": eagleeye_score,
            "roots": roots_score,
            "bondDesk": bond_score,
            "hawkeye": hawkeye_score,
        }
        wf["overallReadinessScore"] = overall
        wf["aiAssessment"] = ai_note
        wf["updatedAt"] = datetime.utcnow().isoformat()
        wf["events"].append({
            "type": "ai_evaluation",
            "score": overall,
            "timestamp": datetime.utcnow().isoformat(),
        })

    return _ok(wf)


@bond_workflow_bp.route("/deal/<deal_id>/checklist", methods=["POST"])
@require_auth()
def update_checklist(deal_id):
    """Add or toggle a checklist item."""
    b = request.get_json() or {}
    wf = _get_or_create_workflow(deal_id)

    item_id = b.get("itemId")
    if item_id:
        # Toggle existing
        with _lock:
            for item in wf["checklist"]:
                if item["id"] == item_id:
                    item["completed"] = not item["completed"]
                    break
    else:
        # Add new
        with _lock:
            wf["checklist"].append({
                "id": f"chk_{len(wf['checklist'])+1}",
                "label": b.get("label", "Untitled item"),
                "category": b.get("category", "general"),
                "completed": False,
                "required": b.get("required", True),
            })

    return _ok(wf)


@bond_workflow_bp.route("/deal/<deal_id>/phase", methods=["PATCH"])
@require_auth()
def update_phase(deal_id):
    b = request.get_json() or {}
    wf = _get_or_create_workflow(deal_id)
    new_phase = b.get("phase")
    valid = ["sourcing", "readiness", "structuring", "placement", "placed", "closed"]
    if new_phase not in valid:
        return _err(f"Invalid phase. Must be one of: {valid}")
    with _lock:
        wf["phase"] = new_phase
        wf["updatedAt"] = datetime.utcnow().isoformat()
        wf["events"].append({
            "type": "phase_change",
            "phase": new_phase,
            "timestamp": datetime.utcnow().isoformat(),
        })
    return _ok(wf)
