import sys
import os
import threading
import time
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

# Ensure backend dir is on path for model imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from routes.fund import fund_bp, register_fund_socket_events
from routes.marketing import marketing_bp
from routes.deals import deals_bp
from routes.auth import auth_bp
from routes.documents import documents_bp
from routes.activity import activity_bp
from routes.agents_api import agents_bp
from routes.market import market_bp
from routes.marketplace import marketplace_bp
from routes.investors import investors_bp
from routes.perm import perm_bp
from routes.ma import ma_bp
from routes.lenders_api import lenders_api_bp
from routes.surety import surety_bp
from routes.due_diligence import dd_bp
from routes.bond_tools import bond_tools_bp
from routes.risk import risk_bp
from routes.blockchain import blockchain_bp
from routes.webhooks import webhooks_bp
from routes.roots import roots_bp
from routes.intelligence import intelligence_bp
from routes.engines_api import engines_bp
from routes.powerstrip import powerstrip_bp
from routes.bond_workflow import bond_workflow_bp
from routes.bond_structuring import bond_structuring_bp
from routes.eagleeye import eagleeye_bp
from routes.hawkeye import hawkeye_bp
from routes.rating_esg import rating_esg_bp
from routes.health import health_bp
from routes.nightvision import nightvision_bp
from routes.treasury import treasury_bp
from routes.phoenix import phoenix_bp
from routes.napkin import napkin_bp
from routes.convergence import convergence_bp
from routes.scanner import scanner_bp
from services.logging_service import init_request_logging
from services.fund_engine import FundEngine
from services.deals import DealsRegistry
from services.auth import AuthService
from services.documents import DocumentRegistry
from services.activity import ActivityFeed
from agents.morgan import MorganAgent
from agents.aria import AriaAgent
from agents.sterling import SterlingAgent
from agents.apex_agent import ApexAgent
from agents.auditor import AuditorAgent
from agents.bond_optimizer import BondOptimizerAgent
from agents.bridge_agent import BridgeAgent
from agents.chain_agent import ChainAgent
from agents.lender_scout import LenderScoutAgent
from agents.maxwell import MaxwellAgent
from agents.merlin import MerlinAgent
from agents.prometheus import PrometheusAgent
from agents.quantum import QuantumAgent
from agents.sentinel import SentinelAgent
from agents.surety_scout import SuretyScoutAgent
from agents.vector_agent import VectorAgent
from agents.bernard import BernardAgent
from routes.desks import desks_bp
from routes.emma import emma_bp
from routes.intelligence_engine_api import intel_engine_bp
from routes.workflow import workflow_bp
from routes.counterparties import counterparties_bp
from routes.mirror_agents import mirror_bp
from routes.v2_compat import v2_compat_bp
from routes.deal_flow import deal_flow_bp
from routes.doc_ingestion import doc_ingestion_bp
from routes.preflight import preflight_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    init_request_logging(app)

    engine = FundEngine()
    app.config["FUND_ENGINE"] = engine
    app.config["DEALS"] = DealsRegistry()
    app.config["MORGAN"] = MorganAgent()
    app.config["ARIA"] = AriaAgent()
    app.config["STERLING"] = SterlingAgent()
    app.config["APEX"] = ApexAgent()
    app.config["AUDITOR"] = AuditorAgent()
    app.config["BOND_OPTIMIZER"] = BondOptimizerAgent()
    app.config["BRIDGE"] = BridgeAgent()
    app.config["CHAIN"] = ChainAgent()
    app.config["LENDER_SCOUT"] = LenderScoutAgent()
    app.config["MAXWELL"] = MaxwellAgent()
    app.config["MERLIN"] = MerlinAgent()
    app.config["PROMETHEUS"] = PrometheusAgent()
    app.config["QUANTUM"] = QuantumAgent()
    app.config["SENTINEL"] = SentinelAgent()
    app.config["SURETY_SCOUT"] = SuretyScoutAgent()
    app.config["VECTOR"] = VectorAgent()
    auth = AuthService()
    app.config["AUTH"] = auth
    app.config["DOCS"] = DocumentRegistry()
    app.config["ACTIVITY"] = ActivityFeed()
    from services.treasury_engine import TreasuryEngine
    app.config["TREASURY_ENGINE"] = TreasuryEngine()
    app.config["BERNARD"] = BernardAgent()
    from services.phoenix_engine import PhoenixEngine
    app.config["PHOENIX_ENGINE"] = PhoenixEngine()

    # Core blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(fund_bp, url_prefix="/api/fund")
    app.register_blueprint(marketing_bp, url_prefix="/api/marketing")
    app.register_blueprint(deals_bp, url_prefix="/api/deals")
    app.register_blueprint(documents_bp, url_prefix="/api/docs")
    app.register_blueprint(activity_bp, url_prefix="/api/activity")

    # New Series 1-2 blueprints
    app.register_blueprint(agents_bp, url_prefix="/api/agents")
    app.register_blueprint(market_bp, url_prefix="/api/market")
    app.register_blueprint(marketplace_bp, url_prefix="/api/marketplace")
    app.register_blueprint(investors_bp, url_prefix="/api/investors")
    app.register_blueprint(perm_bp, url_prefix="/api/perm")
    app.register_blueprint(ma_bp, url_prefix="/api/ma")
    app.register_blueprint(lenders_api_bp, url_prefix="/api/lenders-direct")
    app.register_blueprint(surety_bp, url_prefix="/api/surety")
    app.register_blueprint(dd_bp, url_prefix="/api/dd")
    app.register_blueprint(bond_tools_bp, url_prefix="/api/bond-tools")
    app.register_blueprint(risk_bp, url_prefix="/api/risk")
    app.register_blueprint(blockchain_bp, url_prefix="/api/blockchain")
    app.register_blueprint(webhooks_bp, url_prefix="/api/webhooks")
    app.register_blueprint(roots_bp, url_prefix="")
    app.register_blueprint(intelligence_bp, url_prefix="")
    app.register_blueprint(engines_bp, url_prefix="/api/engines")
    app.register_blueprint(powerstrip_bp, url_prefix="/api/powerstrip")
    app.register_blueprint(bond_workflow_bp, url_prefix="/api/bond-workflow")
    app.register_blueprint(eagleeye_bp, url_prefix="/api/eagleeye")
    app.register_blueprint(hawkeye_bp, url_prefix="/api/hawkeye")
    app.register_blueprint(rating_esg_bp, url_prefix="/api/rating-esg")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(nightvision_bp, url_prefix="/api/nightvision")
    app.register_blueprint(bond_structuring_bp, url_prefix="/api/bond-structuring")
    app.register_blueprint(treasury_bp, url_prefix="/api/treasury")
    app.register_blueprint(phoenix_bp, url_prefix="/api/phoenix")
    app.register_blueprint(napkin_bp, url_prefix="/api/napkin")
    from services.convergence_engine import ConvergenceEngine
    app.config["CONVERGENCE_ENGINE"] = ConvergenceEngine()
    app.register_blueprint(convergence_bp, url_prefix="/api/convergence")
    from services.autonomous_scanner import AutonomousScanner
    app.config["SCANNER"] = AutonomousScanner(convergence_engine=app.config["CONVERGENCE_ENGINE"])
    app.register_blueprint(scanner_bp, url_prefix="/api/scanner")

    # Operating Framework v1 — Desk Registry + Bernard CEO + EMMA Intelligence
    app.register_blueprint(desks_bp, url_prefix="/api/desks")
    app.register_blueprint(emma_bp, url_prefix="/api/emma")
    app.register_blueprint(intel_engine_bp, url_prefix="/api/intel")
    app.register_blueprint(workflow_bp, url_prefix="/api/workflow")
    app.register_blueprint(counterparties_bp, url_prefix="/api/counterparties")
    app.register_blueprint(mirror_bp, url_prefix="/api/rating")
    app.register_blueprint(v2_compat_bp, url_prefix="/api")
    app.register_blueprint(deal_flow_bp, url_prefix="/api/deal-flow")
    app.register_blueprint(doc_ingestion_bp, url_prefix="/api/docs/ingest")
    app.register_blueprint(preflight_bp, url_prefix="/api/preflight")

    # Seed EMMA with real bond structures on startup
    from services.emma_seed_data import seed_emma_database
    seed_count = seed_emma_database()
    app.logger.info(f"EMMA seeded with {seed_count} bond structures")

    @app.get("/api/metrics")
    def metrics():
        from routes.deals import _deals, _bonds, _lock
        with _lock:
            deal_count = len(_deals)
            active = sum(1 for d in _deals.values() if d["status"] != "closed")
            total_pipeline = sum(
                d.get("project", {}).get("total_project_cost_usd", 0)
                for d in _deals.values() if d["status"] != "closed"
            )
            bond_count = len(_bonds)
        return jsonify({
            "success": True,
            "data": {
                "total_deals": deal_count,
                "active_deals": active,
                "total_pipeline_usd": total_pipeline,
                "bond_structures": bond_count,
                "agents_active": 16,
                "agents_total": len(__import__("agents.desk_registry", fromlist=["get_all_agents"]).get_all_agents()),
            },
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })

    is_serverless = os.environ.get("VERCEL") == "1"

    if not is_serverless:
        socketio = SocketIO(
            app,
            cors_allowed_origins=Config.FRONTEND_ORIGIN,
            async_mode="threading",
        )
        register_fund_socket_events(socketio, engine, auth)
        app.config["SOCKETIO"] = socketio

        def ticker():
            while True:
                time.sleep(Config.FUND_TICK_SECONDS)
                snapshot = engine.tick_all()
                for client_id, payload in snapshot.items():
                    socketio.emit("fund_update", payload, to=f"client:{client_id}")
                socketio.emit("market_update", engine.market_snapshot())

        threading.Thread(target=ticker, daemon=True).start()
        return app, socketio
    else:
        return app, None


app, socketio = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"NEST backend starting on {host}:{port} — {len(app.url_map._rules)} routes")
    if socketio:
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=False)
