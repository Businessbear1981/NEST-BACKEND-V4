"""NEST Intelligence Routes — Bond Intel + Monitor + AI Router"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth, current_user
from datetime import datetime

intelligence_bp = Blueprint("intelligence", __name__)

try:
    from services.core import ok, err
except ImportError:
    def ok(d, c=200):
        return jsonify({"success": True, "data": d, "timestamp": datetime.utcnow().isoformat()}), c

    def err(m, c=400):
        return jsonify({"success": False, "error": m, "timestamp": datetime.utcnow().isoformat()}), c

from services.bond_intelligence import (bond_intel, BOND_TYPES, GRADING_CRITERIA,
                                        MILESTONE_GATES, PROFESSIONAL_TEAM,
                                        HUNDRED_PCT_FINANCING, REQUIRED_DOCUMENTS)
from services.project_monitor import project_monitor
from services.ai_router import ai_router
from services.phase_bond_engine import phase_bond_engine
from services.ma_bond_engine import ma_bond_engine, MA_BOND_RULES
from services.forensic_audit import forensic_audit, AUDIT_STANDARDS
from services.bridge_fund import bridge_fund
from services.licensing import licensing_service
from services.ingestion import ingestion_layer
import services.data_connectors  # registers all data plugins on import
from services.auth import require_auth


# ── BOND INTELLIGENCE ─────────────────────────────────────────

@intelligence_bp.route("/api/bond-intel/types", methods=["GET"])
@require_auth()
def bond_types():
    return ok(BOND_TYPES)


@intelligence_bp.route("/api/bond-intel/grading", methods=["GET"])
@require_auth()
def grading():
    return ok(GRADING_CRITERIA)


@intelligence_bp.route("/api/bond-intel/milestones", methods=["GET"])
@require_auth()
def milestones():
    return ok(MILESTONE_GATES)


@intelligence_bp.route("/api/bond-intel/team", methods=["GET"])
@require_auth()
def team():
    return ok(PROFESSIONAL_TEAM)


@intelligence_bp.route("/api/bond-intel/documents", methods=["GET"])
@require_auth()
def documents():
    bond_type = request.args.get("bond_type", "REVENUE_BOND")
    return ok(REQUIRED_DOCUMENTS.get(bond_type, REQUIRED_DOCUMENTS["REVENUE_BOND"]))


@intelligence_bp.route("/api/bond-intel/100pct-path", methods=["GET"])
@require_auth()
def hundred_pct():
    return ok(HUNDRED_PCT_FINANCING)


@intelligence_bp.route("/api/bond-intel/rating-readiness", methods=["POST"])
@require_auth()
def rating_readiness():
    body = request.get_json() or {}
    return ok(bond_intel.assess_rating_readiness(body))


@intelligence_bp.route("/api/bond-intel/financing-path", methods=["POST"])
@require_auth()
def financing_path():
    body = request.get_json() or {}
    return ok(bond_intel.get_financing_path(
        body.get("stage", "pre_development"),
        body.get("loan_amount_usd", 0),
        body.get("presales_pct", 0)
    ))


@intelligence_bp.route("/api/bond-intel/milestone-status", methods=["POST"])
@require_auth()
def milestone_status():
    body = request.get_json() or {}
    return ok(bond_intel.get_milestone_status(
        body.get("current_gate", 1),
        body.get("presales_pct", 0),
        body.get("has_feasibility", False),
        body.get("has_GMP", False)
    ))


# ── PROJECT MONITOR ───────────────────────────────────────────

@intelligence_bp.route("/api/monitor/projects", methods=["POST"])
@require_auth()
def create_project():
    body = request.get_json() or {}
    if not body.get("deal_id"):
        return err("deal_id required")
    return ok(project_monitor.create_project(body["deal_id"], body)), 201


@intelligence_bp.route("/api/monitor/projects/<deal_id>", methods=["GET"])
@require_auth()
def get_dashboard(deal_id):
    return ok(project_monitor.get_dashboard(deal_id))


@intelligence_bp.route("/api/monitor/projects/<deal_id>/draw", methods=["POST"])
@require_auth()
def record_draw(deal_id):
    body = request.get_json() or {}
    return ok(project_monitor.record_draw(deal_id, body))


@intelligence_bp.route("/api/monitor/projects/<deal_id>/presale", methods=["POST"])
@require_auth()
def record_presale(deal_id):
    body = request.get_json() or {}
    return ok(project_monitor.record_presale(
        deal_id, body.get("unit_type", "ILU"),
        body.get("unit_number", ""), body.get("deposit_usd", 0),
        body.get("binding", False)
    ))


@intelligence_bp.route("/api/monitor/projects/<deal_id>/alert/<alert_id>/ack", methods=["PATCH"])
@require_auth()
def ack_alert(deal_id, alert_id):
    p = project_monitor.projects.get(deal_id)
    if not p:
        return err("Not found", 404)
    for a in p.get("alerts", []):
        if a["id"] == alert_id:
            a["acknowledged"] = True
            return ok({"acknowledged": True, "alert_id": alert_id})
    return err("Alert not found", 404)


# ── AI ROUTER ─────────────────────────────────────────────────

@intelligence_bp.route("/api/ai/status", methods=["GET"])
@require_auth()
def ai_status():
    return ok(ai_router.get_tool_status())


@intelligence_bp.route("/api/ai/market-rates", methods=["GET"])
@require_auth()
def market_rates():
    return ok(ai_router.get_market_rates())


@intelligence_bp.route("/api/ai/route", methods=["POST"])
@require_auth()
def route_task():
    body = request.get_json() or {}
    if not body.get("prompt"):
        return err("prompt required")
    return ok(ai_router.route(
        task_type=body.get("task_type", "credit_memo"),
        prompt=body["prompt"],
        system=body.get("system"),
        force_tool=body.get("force_tool"),
    ))


# ── PHASE BOND ENGINE ─────────────────────────────────────────

@intelligence_bp.route("/api/phase-bonds/structure", methods=["POST"])
@require_auth()
def phase_bond_structure():
    body = request.get_json() or {}
    if not body.get("total_project_cost_usd"):
        return err("total_project_cost_usd required")
    return ok(phase_bond_engine.structure_phase_bonds(
        body["total_project_cost_usd"],
        body.get("base_rate_bps", 650),
        body.get("project_type", "senior_living")
    ))


@intelligence_bp.route("/api/phase-bonds/phases", methods=["GET"])
@require_auth()
def phase_bond_phases():
    return ok(phase_bond_engine.PHASES)


@intelligence_bp.route("/api/phase-bonds/economics", methods=["POST"])
@require_auth()
def phase_bond_economics():
    body = request.get_json() or {}
    structure = phase_bond_engine.structure_phase_bonds(
        body.get("total_project_cost_usd", 200_000_000),
        body.get("base_rate_bps", 650),
        body.get("project_type", "senior_living")
    )
    return ok(phase_bond_engine.compute_nest_economics(structure["phases"]))


@intelligence_bp.route("/api/phase-bonds/calls-puts", methods=["POST"])
@require_auth()
def phase_bond_calls_puts():
    body = request.get_json() or {}
    structure = phase_bond_engine.structure_phase_bonds(
        body.get("total_project_cost_usd", 200_000_000),
        body.get("base_rate_bps", 650)
    )
    scenarios = body.get("rate_scenarios", [
        {"name": "rates_down_100", "rate_bps": 550},
        {"name": "rates_up_100", "rate_bps": 750},
        {"name": "rates_up_200", "rate_bps": 850},
    ])
    return ok(phase_bond_engine.optimize_calls_puts(structure["phases"], scenarios))


# ── M&A BOND ENGINE ───────────────────────────────────────────

@intelligence_bp.route("/api/ma-bonds/rules", methods=["GET"])
@require_auth()
def ma_bond_rules():
    return ok(MA_BOND_RULES)


@intelligence_bp.route("/api/ma-bonds/structure", methods=["POST"])
@require_auth()
def ma_bond_structure():
    body = request.get_json() or {}
    company = body.get("company", {})
    terms = body.get("acquisition_terms", {})
    if not company.get("ebitda_usd"):
        return err("company.ebitda_usd required")
    return ok(ma_bond_engine.structure_acquisition_bond(company, terms))


@intelligence_bp.route("/api/ma-bonds/pik-analysis", methods=["POST"])
@require_auth()
def ma_pik_analysis():
    body = request.get_json() or {}
    return ok(ma_bond_engine.model_pik_vs_cash_pay(
        body.get("bond_amount_usd", 100_000_000),
        body.get("coupon_pct", 12),
        body.get("hold_years", 5),
        body.get("ebitda_growth_pct", 10)
    ))


@intelligence_bp.route("/api/ma-bonds/balance-sheet", methods=["POST"])
@require_auth()
def ma_balance_sheet():
    body = request.get_json() or {}
    return ok(ma_bond_engine.balance_sheet_analysis(
        body.get("company", {}),
        body.get("bond_structure", {})
    ))


# ── FORENSIC AUDIT ────────────────────────────────────────────

@intelligence_bp.route("/api/audit/standards", methods=["GET"])
@require_auth()
def audit_standards():
    return ok(AUDIT_STANDARDS)


@intelligence_bp.route("/api/audit/run", methods=["POST"])
@require_auth()
def run_audit():
    body = request.get_json() or {}
    return ok(forensic_audit.run_full_audit(
        body.get("deal", {}),
        body.get("documents", {}),
        body.get("financials", {})
    ))


@intelligence_bp.route("/api/audit/sources-uses", methods=["POST"])
@require_auth()
def audit_sources_uses():
    body = request.get_json() or {}
    return ok(forensic_audit.validate_sources_uses(
        body.get("sources_uses", {}),
        body.get("bank_records", [])
    ))


@intelligence_bp.route("/api/audit/assumptions", methods=["POST"])
@require_auth()
def audit_assumptions():
    body = request.get_json() or {}
    return ok(forensic_audit.validate_assumptions(
        body.get("projections", {}),
        body.get("market_comps", [])
    ))


@intelligence_bp.route("/api/audit/rating-presentation", methods=["POST"])
@require_auth()
def audit_rating_presentation():
    body = request.get_json() or {}
    return ok(forensic_audit.rating_agency_presentation(
        body.get("deal", {}),
        body.get("audit", {}),
        body.get("target_agency", "SP")
    ))


@intelligence_bp.route("/api/audit/bank-presentation", methods=["POST"])
@require_auth()
def audit_bank_presentation():
    body = request.get_json() or {}
    return ok(forensic_audit.bank_presentation(
        body.get("deal", {}),
        body.get("audit", {}),
        body.get("bank", "JPMorgan")
    ))


# ── BRIDGE FUND ───────────────────────────────────────────────

@intelligence_bp.route("/api/bridge/underwrite", methods=["POST"])
@require_auth()
def bridge_underwrite():
    body = request.get_json() or {}
    if not body.get("amount_usd"):
        return err("amount_usd required")
    return ok(bridge_fund.underwrite_bridge(
        body.get("deal", {}),
        body["amount_usd"],
        body.get("use_of_proceeds", "soft_costs")
    ))


@intelligence_bp.route("/api/bridge/equity-value", methods=["POST"])
@require_auth()
def bridge_equity_value():
    body = request.get_json() or {}
    return ok(bridge_fund.calculate_equity_value(
        body.get("deal", {}),
        body.get("equity_pct", 12.5),
        body.get("exit_ev_usd", 0)
    ))


@intelligence_bp.route("/api/bridge/portfolio", methods=["GET"])
@require_auth()
def bridge_portfolio():
    return ok(bridge_fund.portfolio_dashboard())


@intelligence_bp.route("/api/bridge/<loan_id>/repay", methods=["POST"])
@require_auth()
def bridge_repay(loan_id):
    body = request.get_json() or {}
    return ok(bridge_fund.repay_loan(loan_id, body.get("repayment_source", "bond_proceeds")))


# ── LICENSING & COMPLIANCE ────────────────────────────────────

@intelligence_bp.route("/api/licensing/roadmap", methods=["GET"])
@require_auth()
def licensing_roadmap():
    return ok(licensing_service.get_roadmap())


@intelligence_bp.route("/api/licensing/status", methods=["GET"])
@require_auth()
def licensing_status():
    return ok(licensing_service.get_current_status())


@intelligence_bp.route("/api/licensing/fees", methods=["GET"])
@require_auth()
def licensing_fees():
    return ok(licensing_service.get_fee_structure())


@intelligence_bp.route("/api/licensing/compliance-calendar", methods=["GET"])
@require_auth()
def compliance_calendar():
    return ok(licensing_service.get_compliance_calendar())


@intelligence_bp.route("/api/licensing/rent-vs-own", methods=["POST"])
@require_auth()
def rent_vs_own():
    body = request.get_json() or {}
    return ok(licensing_service.calculate_rent_vs_own(
        body.get("annual_fees_usd", 0)
    ))


@intelligence_bp.route("/api/licensing/finra-letter", methods=["POST"])
@require_auth()
def finra_letter():
    letter = licensing_service.generate_finra_sponsorship_request()
    return ok({"letter": letter})


@intelligence_bp.route("/api/licensing/exam/<exam_name>", methods=["GET"])
@require_auth()
def exam_detail(exam_name):
    return ok(licensing_service.get_exam_study_plan(exam_name))


# ── INGESTION LAYER (Central Nervous System) ──────────────────

@intelligence_bp.route("/api/nervous-system/dashboard", methods=["GET"])
@require_auth()
def nervous_system_dashboard():
    return ok(ingestion_layer.get_dashboard())


@intelligence_bp.route("/api/nervous-system/ingest", methods=["POST"])
@require_auth()
def nervous_system_ingest():
    body = request.get_json() or {}
    if not body.get("prompt"):
        return err("prompt required")
    return ok(ingestion_layer.ingest(
        task_type=body.get("task_type", "credit_memo"),
        prompt=body["prompt"],
        force_plugin=body.get("force_plugin"),
        system=body.get("system"),
    ))


@intelligence_bp.route("/api/nervous-system/multi-ingest", methods=["POST"])
@require_auth()
def nervous_system_multi():
    body = request.get_json() or {}
    if not body.get("prompt"):
        return err("prompt required")
    return ok(ingestion_layer.multi_ingest(
        task_type=body.get("task_type", "second_opinion"),
        prompt=body["prompt"],
        plugins=body.get("plugins"),
    ))


@intelligence_bp.route("/api/nervous-system/plugin/<plugin_name>", methods=["GET"])
@require_auth()
def nervous_system_plugin(plugin_name):
    plugin = ingestion_layer.get_plugin(plugin_name)
    if not plugin:
        return err(f"Plugin '{plugin_name}' not found", 404)
    health = plugin.health_check()
    health["capabilities"] = plugin.capabilities
    health["description"] = plugin.description
    return ok(health)


@intelligence_bp.route("/api/nervous-system/proofread", methods=["POST"])
@require_auth()
def nervous_system_proofread():
    body = request.get_json() or {}
    if not body.get("text"):
        return err("text required")
    return ok(ingestion_layer.ingest(
        task_type="proofread",
        prompt=body["text"],
        document_text=body["text"],
        check_type=body.get("check_type", "full"),
    ))


@intelligence_bp.route("/api/nervous-system/video", methods=["POST"])
@require_auth()
def nervous_system_video():
    body = request.get_json() or {}
    if not body.get("prompt"):
        return err("prompt required")
    return ok(ingestion_layer.ingest(
        task_type="marketing_video",
        prompt=body["prompt"],
        video_type=body.get("video_type", "marketing"),
        duration_seconds=body.get("duration_seconds", 30),
        style=body.get("style", "cinematic"),
    ))


@intelligence_bp.route("/api/nervous-system/log", methods=["GET"])
@require_auth()
def nervous_system_log():
    limit = request.args.get("limit", 50, type=int)
    return ok(ingestion_layer.call_log[-limit:])


# ── DATA CONNECTORS ───────────────────────────────────────────

@intelligence_bp.route("/api/data/market-rates", methods=["GET"])
@require_auth()
def data_market_rates():
    fred = ingestion_layer.get_plugin("fred")
    if fred:
        return ok(fred.get_market_snapshot() if hasattr(fred, 'get_market_snapshot') else fred.execute())
    return ok({"source": "fallback", "treasury_10yr": 4.28, "sofr": 5.33})


@intelligence_bp.route("/api/data/treasury", methods=["GET"])
@require_auth()
def data_treasury():
    series = request.args.get("series", "DGS10")
    limit = request.args.get("limit", 10, type=int)
    fred = ingestion_layer.get_plugin("fred")
    if fred:
        return ok(fred.execute(series_id=series, limit=limit))
    return err("FRED plugin not available")


@intelligence_bp.route("/api/data/construction-costs", methods=["POST"])
@require_auth()
def data_construction_costs():
    body = request.get_json() or {}
    rsmeans = ingestion_layer.get_plugin("rsmeans")
    if rsmeans:
        return ok(rsmeans.execute(
            building_type=body.get("building_type", "senior_living_ilu"),
            region=body.get("region", "national"),
            square_footage=body.get("square_footage", 0),
        ))
    return err("RSMeans plugin not available")


@intelligence_bp.route("/api/data/edgar-search", methods=["POST"])
@require_auth()
def data_edgar_search():
    body = request.get_json() or {}
    edgar = ingestion_layer.get_plugin("edgar")
    if edgar:
        return ok(edgar.execute(
            company=body.get("company", ""),
            filing_type=body.get("filing_type", "10-K"),
        ))
    return err("EDGAR plugin not available")


@intelligence_bp.route("/api/data/emma-search", methods=["POST"])
@require_auth()
def data_emma_search():
    body = request.get_json() or {}
    emma = ingestion_layer.get_plugin("emma")
    if emma:
        return ok(emma.execute(
            cusip=body.get("cusip", ""),
            issuer=body.get("issuer", ""),
        ))
    return err("EMMA plugin not available")


@intelligence_bp.route("/api/data/brokercheck", methods=["POST"])
@require_auth()
def data_brokercheck():
    body = request.get_json() or {}
    bc = ingestion_layer.get_plugin("finra_brokercheck")
    if bc:
        return ok(bc.execute(name=body.get("name", ""), crd_number=body.get("crd", "")))
    return err("BrokerCheck plugin not available")


@intelligence_bp.route("/api/data/property", methods=["POST"])
@require_auth()
def data_property():
    body = request.get_json() or {}
    attom = ingestion_layer.get_plugin("attom")
    if attom:
        return ok(attom.execute(address=body.get("address", "")))
    return err("ATTOM plugin not available — set ATTOM_API_KEY")
