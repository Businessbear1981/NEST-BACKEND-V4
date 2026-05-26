"""Full deal lifecycle routes — CRUD, bond structure, refi, covenants, checklist, memo.

Backed by Supabase. Falls back to in-memory if DB is not configured.
"""
import json
import threading
import uuid as _uuid
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
from models.deal import new_deal, compute_readiness_score, DEAL_STATUSES
from models.bond import new_bond_structure, new_series
from models.refi import new_refi_cycle
from services.auth import require_auth

try:
    from services.database import db
except ImportError:
    db = None

deals_bp = Blueprint("deals", __name__)

# In-memory fallback (only used when Supabase is not configured)
_lock = threading.RLock()
_deals = {}
_bonds = {}
_refis = {}
_covenants = {}


def _ts():
    return datetime.utcnow().isoformat()


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": _ts()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg, "timestamp": _ts()}), code


def _use_db():
    return db and db.configured


# ── Supabase <-> Deal model mapping ──────────────────────────────

def _deal_to_row(d):
    """Convert in-memory deal dict to Supabase row."""
    project = d.get("project", {})
    return {
        "name": d["name"],
        "status": _map_status(d.get("status", "intake")),
        "state": project.get("state"),
        "market": project.get("city"),
        "deal_type": project.get("asset_type", "bond"),
        "bond_face": project.get("total_project_cost_usd", 0),
        "readiness_score": d.get("readiness_score", 0),
        "checklist": json.dumps(d.get("readiness_checklist", {})),
        "notes": json.dumps({
            "project": d.get("project", {}),
            "sponsor": d.get("sponsor", {}),
            "team": d.get("team", {}),
            "slug": d.get("slug", ""),
        }),
    }


def _row_to_deal(row):
    """Convert Supabase row to deal dict for API response."""
    notes = row.get("notes") or {}
    if isinstance(notes, str):
        try:
            notes = json.loads(notes)
        except (json.JSONDecodeError, TypeError):
            notes = {}

    checklist = row.get("checklist") or {}
    if isinstance(checklist, str):
        try:
            checklist = json.loads(checklist)
        except (json.JSONDecodeError, TypeError):
            checklist = {}

    return {
        "id": row["id"],
        "name": row["name"],
        "slug": notes.get("slug", row["name"].lower().replace(" ", "-")),
        "status": row.get("status", "pipeline"),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
        "readiness_score": row.get("readiness_score", 0),
        "readiness_checklist": checklist if isinstance(checklist, dict) else {},
        "project": notes.get("project", {
            "name": row["name"],
            "state": row.get("state"),
            "city": row.get("market"),
            "asset_type": row.get("deal_type"),
            "total_project_cost_usd": float(row.get("bond_face", 0)),
        }),
        "sponsor": notes.get("sponsor", {}),
        "team": notes.get("team", {}),
        # Supabase-specific fields
        "bond_face": float(row.get("bond_face", 0)),
        "dscr": float(row.get("dscr", 0)),
        "ltv": float(row.get("ltv", 0)),
        "cf_leverage": float(row.get("cf_leverage", 0)),
        "bs_leverage": float(row.get("bs_leverage", 0)),
        "d_ebitda": float(row.get("d_ebitda", 0)),
        "icr": float(row.get("icr", 0)),
        "refi_cycles": row.get("refi_cycles", 0),
        "ae_economics": float(row.get("ae_economics", 0)),
        "state": row.get("state"),
        "market": row.get("market"),
        "stress_scenarios": row.get("stress_scenarios", []),
        "capital_stack": row.get("capital_stack", []),
        "sources_uses": row.get("sources_uses", []),
    }


def _map_status(status):
    """Map in-memory statuses to Supabase CHECK constraint values."""
    mapping = {
        "intake": "pipeline",
        "underwriting": "active",
        "structured": "active",
        "placed": "active",
        "active": "active",
        "refi_cycle": "active",
        "bridge": "active",
        "closed": "closed",
    }
    return mapping.get(status, status)


# ── Seed (in-memory fallback only) ───────────────────────────────

def _seed():
    seeds = [
        {
            "name": "Life Star Pointe Loop",
            "project": {
                "name": "Life Star Pointe Loop",
                "address": "426 Pointe Loop Blvd",
                "city": "Kissimmee", "state": "FL", "zip": "34747",
                "asset_type": "senior_living", "project_type": "greenfield",
                "total_project_cost_usd": 231_000_000,
                "units": 364, "description": "364-unit IL/AL/MC campus"
            },
            "sponsor": {
                "entity_name": "Life Star Senior Living LLC",
                "contact_name": "Development Team", "track_record_projects": 8,
            },
        },
        {
            "name": "Meridian Cove",
            "project": {
                "name": "Meridian Cove Mixed-Use",
                "city": "Tampa", "state": "FL",
                "asset_type": "mixed_use", "project_type": "greenfield",
                "total_project_cost_usd": 142_000_000,
                "units": 280, "description": "280 units + 45K SF retail"
            },
            "sponsor": {"entity_name": "Meridian Development Group"},
        },
        {
            "name": "Palmetto Ridge",
            "project": {
                "name": "Palmetto Ridge Industrial",
                "city": "Lakeland", "state": "FL",
                "asset_type": "industrial", "project_type": "shovel_ready",
                "total_project_cost_usd": 78_000_000,
                "square_footage": 425_000,
                "description": "425K SF Class A industrial / cold storage"
            },
            "sponsor": {"entity_name": "Palmetto Industrial Partners"},
        },
    ]
    with _lock:
        for s in seeds:
            d = new_deal(s["name"], s.get("project"), s.get("sponsor"))
            d["status"] = "underwriting"
            _deals[d["id"]] = d


if not (_use_db()):
    _seed()


# ── Deal CRUD ───────────────────────────────────────────────────

@deals_bp.route("", methods=["POST"])
@require_auth()
def create_deal():
    body = request.get_json() or {}
    name = body.get("name")
    if not name:
        return _err("name is required")

    if _use_db():
        row = _deal_to_row(new_deal(name, body.get("project"), body.get("sponsor")))
        result = db.insert("deals", row)
        if not result:
            return _err("Failed to create deal", 500)
        return _ok(_row_to_deal(result[0] if isinstance(result, list) else result), 201)

    d = new_deal(name, body.get("project"), body.get("sponsor"))
    with _lock:
        _deals[d["id"]] = d
    return _ok(d, 201)


@deals_bp.route("", methods=["GET"])
@require_auth()
def list_deals():
    status = request.args.get("status")

    if _use_db():
        params = {"order": "created_at.desc"}
        if status:
            params["status"] = f"eq.{status}"
        rows = db.select("deals", params)
        return _ok([_row_to_deal(r) for r in (rows or [])])

    with _lock:
        result = list(_deals.values())
    if status:
        result = [d for d in result if d["status"] == status]
    result.sort(key=lambda d: d["created_at"], reverse=True)
    return _ok(result)


@deals_bp.route("/<deal_id>", methods=["GET"])
@require_auth()
def get_deal(deal_id):
    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        return _ok(_row_to_deal(rows[0]))

    with _lock:
        d = _deals.get(deal_id)
    if not d:
        return _err("Deal not found", 404)
    return _ok(d)


@deals_bp.route("/<deal_id>", methods=["PATCH"])
@require_auth()
def update_deal(deal_id):
    body = request.get_json() or {}

    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        update_data = {}
        if "status" in body:
            mapped = _map_status(body["status"])
            if mapped in ("pipeline", "active", "closing", "closed", "dead"):
                update_data["status"] = mapped
        if "name" in body:
            update_data["name"] = body["name"]
        if "state" in body:
            update_data["state"] = body["state"]
        if "bond_face" in body:
            update_data["bond_face"] = body["bond_face"]
        if "dscr" in body:
            update_data["dscr"] = body["dscr"]
        if "ltv" in body:
            update_data["ltv"] = body["ltv"]
        if "readiness_score" in body:
            update_data["readiness_score"] = body["readiness_score"]
        # Handle nested project/sponsor via notes column
        if "project" in body or "sponsor" in body or "team" in body:
            existing = _row_to_deal(rows[0])
            notes = {
                "project": {**existing.get("project", {}), **(body.get("project", {}))},
                "sponsor": {**existing.get("sponsor", {}), **(body.get("sponsor", {}))},
                "team": {**existing.get("team", {}), **(body.get("team", {}))},
                "slug": existing.get("slug", ""),
            }
            update_data["notes"] = json.dumps(notes)
            if "state" not in update_data and body.get("project", {}).get("state"):
                update_data["state"] = body["project"]["state"]
            if "market" not in update_data and body.get("project", {}).get("city"):
                update_data["market"] = body["project"]["city"]

        if update_data:
            db.update("deals", {"id": f"eq.{deal_id}"}, update_data)
        updated = db.select("deals", {"id": f"eq.{deal_id}"})
        return _ok(_row_to_deal(updated[0]))

    with _lock:
        d = _deals.get(deal_id)
        if not d:
            return _err("Deal not found", 404)
        if "status" in body and body["status"] in DEAL_STATUSES:
            d["status"] = body["status"]
        if "project" in body:
            d["project"].update(body["project"])
        if "sponsor" in body:
            d["sponsor"].update(body["sponsor"])
        if "team" in body:
            d["team"].update(body["team"])
        d["updated_at"] = _ts()
    return _ok(d)


# ── Bond Structure ──────────────────────────────────────────────

@deals_bp.route("/<deal_id>/bond", methods=["POST"])
@require_auth()
def create_bond(deal_id):
    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        deal = _row_to_deal(rows[0])
    else:
        with _lock:
            if deal_id not in _deals:
                return _err("Deal not found", 404)
            deal = _deals[deal_id]

    body = request.get_json() or {}
    structure_type = body.get("structure_type", "dual_tranche")
    series_input = body.get("series", [])
    series_list = []

    if not series_input:
        tpc = deal.get("project", {}).get("total_project_cost_usd", 0) or float(deal.get("bond_face", 100_000_000))
        a_face = tpc * 0.75
        b_face = tpc * 0.07
        series_list.append(new_series("A", a_face, 75, 7.0, 5))
        series_list.append(new_series("B", b_face, 82, 12.0, 5))
    else:
        for s in series_input:
            series_list.append(new_series(
                s.get("label", "A"), s.get("face_amount_usd", 0),
                s.get("ltc_pct", 75), s.get("coupon_rate_pct", 7.0),
                s.get("duration_years", 5),
            ))

    bond = new_bond_structure(deal_id, structure_type, series_list)
    total_face = sum(s["face_amount_usd"] for s in series_list)
    bond["capital_stack"] = {
        "total_raise_usd": total_face * 1.065,
        "project_proceeds_usd": total_face,
        "coupon_reserve_usd": total_face * 0.025,
        "surety_premium_usd": total_face * 0.015,
        "arrangement_fee_usd": total_face * 0.025,
        "contingency_usd": total_face * 0.005,
        "io_impound_usd": total_face * 0.02,
    }

    if _use_db():
        for s in series_list:
            db.insert("bond_structures", {
                "deal_id": deal_id,
                "tranche": s["label"],
                "amount": s["face_amount_usd"],
                "pct": s["ltc_pct"],
                "rate": f"{s['coupon_rate_pct']}%",
                "grade": s.get("rating_target"),
                "coupon": s["coupon_rate_pct"],
                "is_io": False,
            })
    else:
        with _lock:
            _bonds[deal_id] = bond

    return _ok(bond, 201)


@deals_bp.route("/<deal_id>/bond", methods=["GET"])
@require_auth()
def get_bond(deal_id):
    if _use_db():
        rows = db.select("bond_structures", {"deal_id": f"eq.{deal_id}", "order": "created_at.asc"})
        if not rows:
            return _err("No bond structure for this deal", 404)
        # Reconstruct bond structure from rows
        series_list = [{
            "series_id": r["id"],
            "label": r["tranche"],
            "face_amount_usd": float(r["amount"]),
            "ltc_pct": float(r.get("pct", 0)),
            "coupon_rate_pct": float(r.get("coupon", 0)),
            "rating_target": r.get("grade"),
            "is_io": r.get("is_io", False),
        } for r in rows]
        return _ok({
            "deal_id": deal_id,
            "series": series_list,
            "structure_type": "dual_tranche" if len(rows) == 2 else "multi_series",
        })

    with _lock:
        bond = _bonds.get(deal_id)
    if not bond:
        return _err("No bond structure for this deal", 404)
    return _ok(bond)


# ── Refi Cycles ─────────────────────────────────────────────────

@deals_bp.route("/<deal_id>/refi", methods=["POST"])
@require_auth()
def trigger_refi(deal_id):
    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        existing = db.select("refi_cycles", {"deal_id": f"eq.{deal_id}"})
        cycle_num = len(existing or []) + 1
        body = request.get_json() or {}
        result = db.insert("refi_cycles", {
            "deal_id": deal_id,
            "cycle_number": cycle_num,
            "status": "pending",
            "target_rate": body.get("trigger", {}).get("rate_at_trigger_pct"),
            "notes": json.dumps(body.get("trigger", {})),
        })
        if not result:
            return _err("Failed to create refi cycle", 500)
        return _ok(result[0] if isinstance(result, list) else result, 201)

    with _lock:
        if deal_id not in _deals:
            return _err("Deal not found", 404)
        bond = _bonds.get(deal_id)
        if not bond:
            return _err("No bond structure — create bond first", 400)
        existing = _refis.get(deal_id, [])
        cycle_num = len(existing) + 1
        refi = new_refi_cycle(deal_id, bond["id"], cycle_num)
        body = request.get_json() or {}
        if "trigger" in body:
            refi["trigger"].update(body["trigger"])
        existing.append(refi)
        _refis[deal_id] = existing
    return _ok(refi, 201)


@deals_bp.route("/<deal_id>/refis", methods=["GET"])
@require_auth()
def list_refis(deal_id):
    if _use_db():
        rows = db.select("refi_cycles", {"deal_id": f"eq.{deal_id}", "order": "cycle_number.asc"})
        return _ok(rows or [])

    with _lock:
        refis = _refis.get(deal_id, [])
    return _ok(refis)


# ── Covenants ───────────────────────────────────────────────────

@deals_bp.route("/<deal_id>/covenants", methods=["GET"])
@require_auth()
def get_covenants(deal_id):
    if _use_db():
        rows = db.select("covenants", {"deal_id": f"eq.{deal_id}"})
        return _ok(rows or [])

    with _lock:
        covs = _covenants.get(deal_id, [])
    return _ok(covs)


@deals_bp.route("/<deal_id>/covenants/test", methods=["POST"])
@require_auth()
def test_covenants(deal_id):
    body = request.get_json() or {}
    metrics = body.get("metrics", {})

    if _use_db():
        covs = db.select("covenants", {"deal_id": f"eq.{deal_id}"})
        if not covs:
            # Create default covenants in DB
            defaults = [
                ("dscr", "minimum", 1.5, "quarterly"),
                ("ltv", "maximum", 75, "quarterly"),
                ("cash_flow_leverage", "maximum", 2.0, "quarterly"),
                ("balance_sheet_leverage", "maximum", 2.5, "quarterly"),
                ("debt_to_ebitda", "maximum", 6.5, "quarterly"),
                ("interest_coverage_ratio", "minimum", 2.25, "quarterly"),
            ]
            for cov_type, _, thresh, freq in defaults:
                db.insert("covenants", {
                    "deal_id": deal_id,
                    "covenant_type": cov_type,
                    "description": f"{cov_type} {_} {thresh}",
                    "threshold_value": thresh,
                    "test_frequency": freq,
                    "in_compliance": True,
                })
            covs = db.select("covenants", {"deal_id": f"eq.{deal_id}"})

        results = []
        for cov in (covs or []):
            metric_val = metrics.get(cov["covenant_type"], 0)
            threshold = float(cov["threshold_value"] or 0)
            # Determine pass/fail based on covenant type name
            if "minimum" in (cov.get("description", "") or ""):
                passed = metric_val >= threshold
            else:
                passed = metric_val <= threshold
            db.update("covenants", {"id": f"eq.{cov['id']}"}, {
                "current_value": metric_val,
                "in_compliance": passed,
            })
            results.append({
                "covenant_id": cov["id"],
                "metric": cov["covenant_type"],
                "value": metric_val,
                "threshold": threshold,
                "passed": passed,
                "status": "green" if passed else "red",
            })
        return _ok(results)

    # In-memory fallback
    with _lock:
        covs = _covenants.get(deal_id, [])
        if not covs:
            bond = _bonds.get(deal_id)
            if bond:
                covs = _default_covenants(deal_id, bond["id"])
                _covenants[deal_id] = covs

    results = []
    for cov in covs:
        metric_val = metrics.get(cov["metric"], cov.get("last_test_value", 0))
        threshold = cov["threshold_value"]
        if cov["threshold_type"] == "minimum":
            passed = metric_val >= threshold
        else:
            passed = metric_val <= threshold
        cov["last_test_date"] = _ts()
        cov["last_test_value"] = metric_val
        cov["status"] = "green" if passed else "red"
        results.append({
            "covenant_id": cov["id"],
            "metric": cov["metric"],
            "value": metric_val,
            "threshold": threshold,
            "threshold_type": cov["threshold_type"],
            "passed": passed,
            "status": cov["status"],
        })
    return _ok(results)


def _default_covenants(deal_id, bond_id):
    defaults = [
        ("dscr", "minimum", 1.5, "quarterly"),
        ("ltv", "maximum", 75, "quarterly"),
        ("cash_flow_leverage", "maximum", 2.0, "quarterly"),
        ("balance_sheet_leverage", "maximum", 2.5, "quarterly"),
        ("debt_to_ebitda", "maximum", 6.5, "quarterly"),
        ("interest_coverage_ratio", "minimum", 2.25, "quarterly"),
        ("occupancy_pct", "minimum", 60, "monthly"),
    ]
    covs = []
    for metric, thresh_type, thresh_val, freq in defaults:
        covs.append({
            "id": str(_uuid.uuid4()),
            "deal_id": deal_id,
            "bond_structure_id": bond_id,
            "covenant_type": "financial_maintenance",
            "metric": metric,
            "threshold_type": thresh_type,
            "threshold_value": thresh_val,
            "test_frequency": freq,
            "last_test_date": None,
            "last_test_value": None,
            "status": "green",
            "cure_period_days": 30,
            "cure_deadline": None,
            "breach_history": [],
        })
    return covs


# ── Readiness Checklist ─────────────────────────────────────────

@deals_bp.route("/<deal_id>/checklist", methods=["GET"])
@require_auth()
def get_checklist(deal_id):
    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        deal = _row_to_deal(rows[0])
        return _ok({
            "checklist": deal["readiness_checklist"],
            "readiness_score": deal["readiness_score"],
        })

    with _lock:
        d = _deals.get(deal_id)
    if not d:
        return _err("Deal not found", 404)
    return _ok({
        "checklist": d["readiness_checklist"],
        "readiness_score": d["readiness_score"],
    })


@deals_bp.route("/<deal_id>/checklist", methods=["PATCH"])
@require_auth()
def update_checklist(deal_id):
    body = request.get_json() or {}

    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        deal = _row_to_deal(rows[0])
        checklist = deal["readiness_checklist"]
        for key, val in body.items():
            if key in checklist:
                checklist[key] = val
        score = compute_readiness_score(checklist)
        db.update("deals", {"id": f"eq.{deal_id}"}, {
            "checklist": json.dumps(checklist),
            "readiness_score": score,
        })
        return _ok({"checklist": checklist, "readiness_score": score})

    with _lock:
        d = _deals.get(deal_id)
        if not d:
            return _err("Deal not found", 404)
        for key, val in body.items():
            if key in d["readiness_checklist"]:
                d["readiness_checklist"][key] = val
        d["readiness_score"] = compute_readiness_score(d["readiness_checklist"])
        d["updated_at"] = _ts()
    return _ok({
        "checklist": d["readiness_checklist"],
        "readiness_score": d["readiness_score"],
    })


# ── Memo Generation ─────────────────────────────────────────────

@deals_bp.route("/<deal_id>/memo", methods=["POST"])
@require_auth()
def generate_memo(deal_id):
    if _use_db():
        rows = db.select("deals", {"id": f"eq.{deal_id}"})
        if not rows:
            return _err("Deal not found", 404)
        d = _row_to_deal(rows[0])
        bond_rows = db.select("bond_structures", {"deal_id": f"eq.{deal_id}"})
        bond = bond_rows if bond_rows else None
    else:
        with _lock:
            d = _deals.get(deal_id)
        if not d:
            return _err("Deal not found", 404)
        bond = _bonds.get(deal_id)

    body = request.get_json() or {}
    memo_type = body.get("memo_type", "executive_summary")
    morgan = current_app.config.get("MORGAN")
    if not morgan:
        return _err("Morgan agent not initialized", 500)
    valid_types = [
        "credit_memo", "executive_summary", "investor_teaser",
        "refi_notice", "term_sheet_cover"
    ]
    content_type = memo_type if memo_type in valid_types else "executive_summary"
    context = {"deal": d, "bond": bond, "memo_type": memo_type}
    result = morgan.generate(content_type, context)
    return _ok(result)


# ── Pipeline Metrics ────────────────────────────────────────────

@deals_bp.route("/pipeline", methods=["GET"])
@require_auth()
def pipeline():
    if _use_db():
        rows = db.select("deals") or []
        active = [r for r in rows if r.get("status") != "closed"]
        total_usd = sum(float(r.get("bond_face", 0)) for r in active)
        by_status = {}
        for r in rows:
            s = r.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        return _ok({
            "total_pipeline_usd": total_usd,
            "deal_count": len(active),
            "by_status": by_status,
        })

    with _lock:
        deals_list = list(_deals.values())
    active = [d for d in deals_list if d["status"] != "closed"]
    total_usd = sum(
        d.get("project", {}).get("total_project_cost_usd", 0) for d in active
    )
    by_status = {}
    for d in deals_list:
        s = d.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    return _ok({
        "total_pipeline_usd": total_usd,
        "deal_count": len(active),
        "by_status": by_status,
    })
