"""Autonomous Scanner API — start/stop the intelligence loop, trigger manual scans."""

from datetime import datetime
from flask import Blueprint, current_app, jsonify

scanner_bp = Blueprint("scanner", __name__)


def _engine():
    return current_app.config["SCANNER"]


def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})


@scanner_bp.get("/status")
def status():
    return _ok(_engine().get_status())


@scanner_bp.post("/start")
def start():
    return _ok(_engine().start())


@scanner_bp.post("/stop")
def stop():
    return _ok(_engine().stop())


@scanner_bp.post("/scan")
def manual_scan():
    """Trigger a single scan cycle manually."""
    return _ok(_engine().run_scan())


@scanner_bp.get("/log")
def scan_log():
    return _ok(_engine().get_log())


@scanner_bp.get("/findings")
def findings():
    return _ok(_engine().get_findings())
