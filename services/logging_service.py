"""
NEST Structured Logging — JSON logs with request IDs, user context, agent tracing.
Phase 3 observability foundation.
"""
import logging
import json
import time
import uuid
import traceback
import functools
from datetime import datetime
from flask import g, request


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(g, "request_id", None) if _has_request_context() else None,
            "user_id": getattr(g, "user_id", None) if _has_request_context() else None,
        }
        if hasattr(record, "extra_data"):
            entry.update(record.extra_data)
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = traceback.format_exception(*record.exc_info)
        return json.dumps(entry, default=str)


def _has_request_context():
    try:
        from flask import has_request_context
        return has_request_context()
    except Exception:
        return False


def get_logger(name: str = "nest") -> logging.Logger:
    """Return a logger configured with JSON output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


_logger = get_logger("nest")


def _extract_user_id():
    """Best-effort JWT decode — never raises."""
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        import jwt
        from config import Config
        token = auth_header[7:]
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub") or payload.get("user_id") or payload.get("email")
    except Exception:
        return None


def init_request_logging(app):
    """Register before/after request hooks for structured logging."""

    @app.before_request
    def _before():
        g.request_id = str(uuid.uuid4())[:12]
        g.request_start = time.perf_counter()
        g.user_id = _extract_user_id()

    @app.after_request
    def _after(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
        duration_ms = (time.perf_counter() - getattr(g, "request_start", time.perf_counter())) * 1000
        # Skip logging health checks to reduce noise
        if not request.path.startswith("/api/health"):
            log_api_request(request.path, request.method, response.status_code, duration_ms)
        return response


def log_api_request(route, method, status_code, duration_ms):
    extra = {"route": route, "method": method, "status_code": status_code,
             "duration_ms": round(duration_ms, 1), "type": "http_request"}
    record = _logger.makeRecord("nest.http", logging.INFO, "", 0,
                                f"{method} {route} {status_code} {round(duration_ms)}ms",
                                (), None)
    record.extra_data = extra
    _logger.handle(record)


def log_agent_run(agent_name, deal_id=None, status="success", duration_ms=0, tokens_used=0):
    extra = {"agent": agent_name, "deal_id": deal_id, "status": status,
             "duration_ms": round(duration_ms, 1), "tokens_used": tokens_used, "type": "agent_run"}
    level = logging.INFO if status == "success" else logging.ERROR
    record = _logger.makeRecord("nest.agent", level, "", 0,
                                f"Agent {agent_name} {status} ({round(duration_ms)}ms)",
                                (), None)
    record.extra_data = extra
    _logger.handle(record)


def log_error(error, context=None):
    extra = {"error": str(error), "context": context or {}, "type": "error"}
    record = _logger.makeRecord("nest.error", logging.ERROR, "", 0,
                                f"Error: {error}", (), None)
    record.extra_data = extra
    _logger.handle(record)


def agent_logged(agent_name, deal_id_param="deal_id"):
    """Decorator for agent methods — auto-logs timing, status, errors."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            deal_id = kwargs.get(deal_id_param)
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                log_agent_run(agent_name, deal_id, "success", duration)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                log_agent_run(agent_name, deal_id, "error", duration)
                log_error(e, {"agent": agent_name, "deal_id": deal_id})
                raise
        return wrapper
    return decorator
