"""GENIE Bond Desk structuring, deal-impact, and pool analysis endpoints."""
from flask import Blueprint, jsonify, request
from datetime import datetime

bond_structuring_bp = Blueprint("bond_structuring", __name__)


def _ts():
    return datetime.utcnow().isoformat()


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": _ts()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg, "timestamp": _ts()}), code


# ── Structure a full capital stack ─────────────────────────────
@bond_structuring_bp.route("/structure", methods=["POST"])
def structure_deal():
    """Takes deal inputs + tranches, returns computed metrics, stress, grade, and Bernard narration."""
    body = request.get_json() or {}
    tranches = body.get("tranches", [])
    deal = body.get("deal", {})

    if not tranches:
        return _err("At least one tranche required")

    from services.core import credit, JPM

    tpc = deal.get("total_project_cost_usd", 0)
    noi = deal.get("stabilized_noi_usd", 0)
    appraised = deal.get("appraised_value_usd", tpc * 1.2)

    # Compute per-tranche metrics
    total_debt = 0
    total_ds = 0
    weighted_coupon_num = 0
    weighted_spread_num = 0
    tranche_results = []

    for t in tranches:
        size = t.get("size_usd", 0)
        coupon = t.get("coupon_pct", 7.0)
        spread = t.get("spread_bps", 0)
        total_debt += size
        ds = size * coupon / 100
        total_ds += ds
        weighted_coupon_num += size * coupon
        weighted_spread_num += size * spread
        tranche_results.append({
            **t,
            "annual_debt_service_usd": round(ds),
        })

    # Aggregate metrics
    blended_coupon = round(weighted_coupon_num / total_debt, 3) if total_debt > 0 else 0
    blended_spread = round(weighted_spread_num / total_debt, 1) if total_debt > 0 else 0
    cltv = round(total_debt / appraised * 100, 2) if appraised > 0 else 0
    ltc = round(total_debt / tpc * 100, 2) if tpc > 0 else 0
    dscr = round(noi / total_ds, 3) if total_ds > 0 else 0
    icr = round(noi / (total_ds * 0.4), 3) if total_ds > 0 else 0

    # Grade using JPM benchmarks
    grade_result = credit.compute({
        "stabilized_noi_usd": noi,
        "a_tranche_usd": total_debt * 0.75,
        "b_tranche_usd": total_debt * 0.25,
        "a_coupon_pct": blended_coupon,
        "b_coupon_pct": blended_coupon + 4,
        "total_project_cost_usd": tpc,
        "appraised_value_usd": appraised,
        "ebitda_usd": noi,
    })

    # Stress test
    stress = credit.stress(noi, total_ds, tpc, total_debt)

    # Bernard narration at three depths
    bernard = {
        "expert": f"{grade_result['obligor_grade']} grade. DSCR {dscr:.2f}x. CLTV {cltv:.1f}%.",
        "standard": f"{grade_result['obligor_grade']} grade structure. DSCR {dscr:.2f}x with {cltv:.1f}% CLTV. "
                     f"{'Investment grade — surety wrap eligible.' if dscr >= 1.5 else 'Sub-IG — requires enhancement.'}",
        "educational": f"This {len(tranches)}-tranche structure raises ${total_debt/1e6:.1f}M against a ${tpc/1e6:.1f}M project. "
                       f"The blended coupon of {blended_coupon:.2f}% produces ${total_ds/1e6:.2f}M annual debt service. "
                       f"With ${noi/1e6:.2f}M NOI, that gives you a {dscr:.2f}x DSCR — "
                       f"{'above the A-grade threshold of 2.0x. Strong position.' if dscr >= 2.0 else 'above BBB threshold of 1.5x. Solid but watch the spread.' if dscr >= 1.5 else 'below investment grade. The 1.5x DSCR floor is the line — you need more NOI or less debt.'} "
                       f"CLTV at {cltv:.1f}% {'is conservative.' if cltv <= 65 else 'is moderate.' if cltv <= 75 else 'is aggressive — LTV alert triggered.'}",
    }

    return _ok({
        "tranches": tranche_results,
        "metrics": {
            "total_debt_usd": round(total_debt),
            "total_debt_service_usd": round(total_ds),
            "blended_coupon_pct": blended_coupon,
            "blended_spread_bps": blended_spread,
            "cltv_pct": cltv,
            "ltc_pct": ltc,
            "dscr": dscr,
            "icr": icr,
            "obligor_grade": grade_result["obligor_grade"],
            "deal_score": grade_result["deal_score"],
            "deal_score_grade": grade_result["deal_score_grade"],
            "ltv_alert": grade_result["ltv_alert"],
        },
        "stress": stress,
        "bernard": bernard,
    })


# ── Deal impact from market movement ──────────────────────────
@bond_structuring_bp.route("/deal-impact", methods=["POST"])
def deal_impact():
    """Compute how a rate change impacts an active deal's stack."""
    body = request.get_json() or {}
    rate_delta_bps = body.get("rate_delta_bps", 0)
    current_stack = body.get("current_stack", {})
    deal = body.get("deal", {})

    blended_coupon = current_stack.get("blended_coupon_pct", 7.0)
    total_debt = current_stack.get("total_debt_usd", 0)
    noi = deal.get("stabilized_noi_usd", 0)

    new_coupon = blended_coupon + rate_delta_bps / 100
    old_ds = total_debt * blended_coupon / 100
    new_ds = total_debt * new_coupon / 100
    old_dscr = round(noi / old_ds, 3) if old_ds > 0 else 0
    new_dscr = round(noi / new_ds, 3) if new_ds > 0 else 0
    dscr_delta = round(new_dscr - old_dscr, 3)

    spread_impact_bps = round(rate_delta_bps * 0.3, 1)

    severity = "favorable" if rate_delta_bps < 0 else "watch" if abs(rate_delta_bps) <= 10 else "action"

    impact_text = (
        f"10yr {'+'if rate_delta_bps > 0 else ''}{rate_delta_bps}bp -> "
        f"coupon {blended_coupon:.2f}%->{new_coupon:.2f}% -> "
        f"DSCR buffer {'+' if dscr_delta > 0 else ''}{dscr_delta:.3f}x"
    )

    return _ok({
        "impact_text": impact_text,
        "severity": severity,
        "rate_delta_bps": rate_delta_bps,
        "coupon_old_pct": blended_coupon,
        "coupon_new_pct": round(new_coupon, 3),
        "dscr_old": old_dscr,
        "dscr_new": new_dscr,
        "dscr_delta": dscr_delta,
        "spread_impact_bps": spread_impact_bps,
        "ds_old_usd": round(old_ds),
        "ds_new_usd": round(new_ds),
    })


# ── Call/Put optionality analysis ─────────────────────────────
@bond_structuring_bp.route("/call-put-analysis", methods=["POST"])
def call_put_analysis():
    """Analyze call/put optionality for a tranche."""
    body = request.get_json() or {}
    from services.core import credit

    current_rate_bps = body.get("current_rate_bps", 0)
    orig_rate_bps = body.get("original_rate_bps", 0)
    deal = body.get("deal", {})

    result = credit.call_put_analysis(current_rate_bps, orig_rate_bps, deal)
    return _ok(result)


# ── CMBS pool analysis ────────────────────────────────────────
@bond_structuring_bp.route("/pool-analysis", methods=["POST"])
def pool_analysis():
    """Analyze a CMBS pool of multiple deals."""
    body = request.get_json() or {}
    deals = body.get("deals", [])

    if not deals:
        return _err("At least one deal required for pool analysis")

    total_commitment = 0
    weighted_coupon_num = 0
    weighted_life_num = 0
    total_noi = 0
    total_ds = 0
    sector_counts = {}
    tranche_classes = {"senior": 0, "mezzanine": 0, "subordinate": 0, "equity": 0}

    for d in deals:
        commitment = d.get("total_debt_usd", 0)
        coupon = d.get("blended_coupon_pct", 7.0)
        wal = d.get("weighted_avg_life_yrs", 10)
        noi = d.get("stabilized_noi_usd", 0)
        ds = commitment * coupon / 100
        sector = d.get("sector", "other")

        total_commitment += commitment
        weighted_coupon_num += commitment * coupon
        weighted_life_num += commitment * wal
        total_noi += noi
        total_ds += ds
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

        for t in d.get("tranches", []):
            series = t.get("series", "A").upper()
            if series == "A":
                tranche_classes["senior"] += t.get("size_usd", 0)
            elif series == "B":
                tranche_classes["mezzanine"] += t.get("size_usd", 0)
            elif series == "C":
                tranche_classes["subordinate"] += t.get("size_usd", 0)
            else:
                tranche_classes["equity"] += t.get("size_usd", 0)

    wac = round(weighted_coupon_num / total_commitment, 3) if total_commitment > 0 else 0
    wal = round(weighted_life_num / total_commitment, 2) if total_commitment > 0 else 0
    pool_dscr = round(total_noi / total_ds, 3) if total_ds > 0 else 0

    unique_sectors = len(sector_counts)
    deal_count = len(deals)
    diversification = min(100, round(unique_sectors * 15 + deal_count * 10))

    senior_pct = round(tranche_classes["senior"] / total_commitment * 100, 1) if total_commitment > 0 else 0

    sub_total = tranche_classes["subordinate"] + tranche_classes["equity"]
    subordination_pct = round(sub_total / total_commitment * 100, 1) if total_commitment > 0 else 0

    return _ok({
        "pool_metrics": {
            "total_commitment_usd": round(total_commitment),
            "deal_count": deal_count,
            "wac_pct": wac,
            "wal_yrs": wal,
            "pool_dscr": pool_dscr,
            "diversification_score": diversification,
            "senior_pct": senior_pct,
            "subordination_pct": subordination_pct,
        },
        "tranche_classes": {k: round(v) for k, v in tranche_classes.items()},
        "sector_breakdown": sector_counts,
    })
