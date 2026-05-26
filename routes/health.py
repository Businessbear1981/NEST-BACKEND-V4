"""Health check endpoints — liveness + readiness with dependency checks."""
import os
import time
import httpx
from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint("health", __name__)

_start_time = time.time()


def _ts():
    return datetime.utcnow().isoformat()


@health_bp.route("/health", methods=["GET"])
def liveness():
    """Fast liveness check — is the process alive?"""
    return jsonify({
        "ok": True,
        "service": "nest-backend",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - _start_time),
        "port": int(os.getenv("PORT", 8000)),
        "timestamp": _ts(),
    })


@health_bp.route("/health/ready", methods=["GET"])
def readiness():
    """Readiness check — test all downstream dependencies."""
    checks = {}
    overall = "healthy"

    # Anthropic API
    checks["anthropic"] = _check_anthropic()

    # FRED API
    checks["fred"] = _check_fred()

    # Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        checks["supabase"] = _check_supabase(supabase_url)
    else:
        checks["supabase"] = {"status": "not_configured", "message": "SUPABASE_URL not set"}

    # Roll up
    statuses = [c["status"] for c in checks.values()]
    if any(s == "unhealthy" for s in statuses):
        overall = "degraded"
    if all(s == "unhealthy" for s in statuses if s != "not_configured"):
        overall = "unhealthy"

    code = 200 if overall == "healthy" else 503
    return jsonify({
        "ok": overall == "healthy",
        "status": overall,
        "checks": checks,
        "uptime_seconds": round(time.time() - _start_time),
        "timestamp": _ts(),
    }), code


def _check_anthropic():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return {"status": "unhealthy", "message": "ANTHROPIC_API_KEY not set"}
    try:
        with httpx.Client(timeout=3) as c:
            r = c.get("https://api.anthropic.com/v1/models",
                       headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
        if r.status_code in (200, 401, 403):
            return {"status": "healthy", "message": "API reachable", "latency_ms": round(r.elapsed.total_seconds() * 1000)}
        return {"status": "degraded", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def _check_fred():
    key = os.getenv("FRED_API_KEY", "")
    if not key:
        return {"status": "unhealthy", "message": "FRED_API_KEY not set"}
    try:
        with httpx.Client(timeout=3) as c:
            r = c.get("https://api.stlouisfed.org/fred/series",
                       params={"series_id": "DGS10", "api_key": key, "file_type": "json"})
        if r.status_code == 200:
            return {"status": "healthy", "message": "FRED reachable", "latency_ms": round(r.elapsed.total_seconds() * 1000)}
        return {"status": "degraded", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def _check_supabase(url):
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not key:
        return {"status": "unhealthy", "message": "SUPABASE_SERVICE_KEY not set"}
    try:
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/rest/v1/",
                       headers={"apikey": key, "Authorization": f"Bearer {key}"})
        if r.status_code in (200, 204):
            return {"status": "healthy", "message": "Supabase reachable", "latency_ms": round(r.elapsed.total_seconds() * 1000)}
        return {"status": "degraded", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}
