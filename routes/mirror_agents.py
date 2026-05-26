"""
Mirror Agents API — Moody's and S&P rating prediction.
The firm's signature capability per Operating Framework.
"""
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request

mirror_bp = Blueprint("mirror", __name__)

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

def _moodys():
    agent = current_app.config.get("MOODYS_MIRROR")
    if not agent:
        from agents.moodys_mirror import MoodysMirrorAgent
        agent = MoodysMirrorAgent()
        current_app.config["MOODYS_MIRROR"] = agent
    return agent

def _sp():
    agent = current_app.config.get("SP_MIRROR")
    if not agent:
        from agents.sp_mirror import SPMirrorAgent
        agent = SPMirrorAgent()
        current_app.config["SP_MIRROR"] = agent
    return agent

@mirror_bp.post("/moodys/predict")
def moodys_predict():
    """Predict Moody's rating for a deal."""
    body = request.get_json(silent=True) or {}
    result = _moodys().predict_rating(body)
    return _ok(result)

@mirror_bp.post("/sp/predict")
def sp_predict():
    """Predict S&P rating for a deal."""
    body = request.get_json(silent=True) or {}
    result = _sp().predict_rating(body)
    return _ok(result)

@mirror_bp.post("/dual")
def dual_predict():
    """Run both Moody's and S&P predictions and compare."""
    body = request.get_json(silent=True) or {}
    moodys_result = _moodys().predict_rating(body)
    sp_result = _sp().predict_rating(body)

    # Cross-reference
    m_rating = moodys_result.get("predicted_rating", "")
    s_rating = sp_result.get("predicted_rating", "")

    return _ok({
        "moodys": moodys_result,
        "sp": sp_result,
        "comparison": {
            "moodys_rating": m_rating,
            "sp_rating": s_rating,
            "split_rating": m_rating != _moodys_to_sp_equivalent(m_rating, s_rating),
            "recommendation": _rating_strategy(m_rating, s_rating),
        },
    })

@mirror_bp.post("/levers")
def levers():
    """Identify structural levers to improve rating from both agencies."""
    body = request.get_json(silent=True) or {}
    m_levers = _moodys().identify_levers(body)
    s_levers = _sp().identify_levers(body)
    return _ok({"moodys_levers": m_levers, "sp_levers": s_levers})

@mirror_bp.post("/moodys/scorecard")
def moodys_scorecard():
    """Get just the Moody's scorecard without AI narrative."""
    body = request.get_json(silent=True) or {}
    result = _moodys().scorecard(body)
    return _ok(result)

def _moodys_to_sp_equivalent(m: str, s: str) -> bool:
    """Check if Moody's and S&P ratings are equivalent."""
    equiv = {
        "Aaa": "AAA", "Aa1": "AA+", "Aa2": "AA", "Aa3": "AA-",
        "A1": "A+", "A2": "A", "A3": "A-",
        "Baa1": "BBB+", "Baa2": "BBB", "Baa3": "BBB-",
        "Ba1": "BB+", "Ba2": "BB", "Ba3": "BB-",
        "B1": "B+", "B2": "B", "B3": "B-",
    }
    return equiv.get(m) == s

def _rating_strategy(m: str, s: str) -> str:
    """Recommend rating strategy based on dual prediction."""
    if m and s:
        return f"Dual-rated: Moody's {m} / S&P {s}. Consider which agency provides better outcome for investor appetite in this sector."
    return "Run both predictions to compare."
