"""
NEST Bridge Surveillance Engine — Silo 14
Post-issuance monitoring: DSCR + MV + permit status + covenant compliance.
"""
from datetime import datetime
from services.core import check_ltv


def monitor_deal(deal: dict, current_metrics: dict,
                 at_issuance_metrics: dict = None) -> dict:
    """
    Generate surveillance snapshot for a post-issuance deal.
    """
    alerts = []
    dscr = current_metrics.get("dscr", 0)
    ltv = current_metrics.get("ltv_pct", 0)
    mv_current = current_metrics.get("market_value", 0)
    mv_issuance = (at_issuance_metrics or {}).get("market_value", mv_current)

    # DSCR monitoring
    if dscr < 1.0:
        alerts.append({"type": "critical", "message": f"DSCR {dscr}x — below 1.0x, surety draw required", "agent": "sentinel"})
    elif dscr < 1.2:
        alerts.append({"type": "warning", "message": f"DSCR {dscr}x — covenant cure period", "agent": "maxwell"})
    elif dscr < 1.5:
        alerts.append({"type": "watch", "message": f"DSCR {dscr}x — below investment grade threshold", "agent": "maxwell"})

    # MV deviation
    if mv_issuance > 0:
        mv_deviation = (mv_current - mv_issuance) / mv_issuance * 100
        if abs(mv_deviation) > 5:
            alerts.append({
                "type": "warning" if mv_deviation < 0 else "info",
                "message": f"MV deviation {mv_deviation:+.1f}% from issuance",
                "agent": "bridge",
            })

    # LTV
    ltv_check = check_ltv(ltv)
    if ltv_check["alert"]:
        alerts.append({"type": "critical", "message": ltv_check["message"], "agent": "sentinel"})

    # Cash trap detection
    cash_trap_dscr = deal.get("cash_trap_dscr_trigger", 1.15)
    cash_trap_active = dscr < cash_trap_dscr
    if cash_trap_active:
        alerts.append({"type": "warning", "message": f"Cash trap triggered — DSCR {dscr}x below {cash_trap_dscr}x trigger", "agent": "bridge"})

    # Occupancy
    occ = current_metrics.get("occupancy_pct", 0)
    occ_target = deal.get("stabilized_occupancy_target", 90)
    if occ < occ_target * 0.85:
        alerts.append({"type": "warning", "message": f"Occupancy {occ}% significantly below {occ_target}% target", "agent": "bridge"})

    return {
        "deal_id": deal.get("id", ""),
        "snapshot_date": datetime.utcnow().isoformat(),
        "current_dscr": dscr,
        "current_ltv": ltv,
        "current_occupancy": occ,
        "market_value": mv_current,
        "mv_at_issuance": mv_issuance,
        "cash_trap_active": cash_trap_active,
        "alerts": alerts,
        "alert_count": len(alerts),
        "critical_count": sum(1 for a in alerts if a["type"] == "critical"),
        "overall_status": "critical" if any(a["type"] == "critical" for a in alerts) else "warning" if alerts else "green",
    }
