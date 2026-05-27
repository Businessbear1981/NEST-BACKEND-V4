"""Preflight Interview API — Bernard-driven Q&A for credit memo completion."""
from datetime import datetime
from flask import Blueprint, jsonify, request

preflight_bp = Blueprint("preflight", __name__)

_answers: dict[str, dict] = {}  # deal_id → {question_id: answer}

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

@preflight_bp.get("/<deal_id>/questions")
def get_questions(deal_id: str):
    from services.preflight_interview import PreflightInterview
    pi = PreflightInterview()
    deal = _get_deal_data(deal_id)
    sections = pi.get_questions(deal)
    status = pi.completion_status(_answers.get(deal_id, {}))
    return _ok({"sections": sections, "status": status})

@preflight_bp.get("/<deal_id>/next")
def next_question(deal_id: str):
    from services.preflight_interview import PreflightInterview
    pi = PreflightInterview()
    deal = _get_deal_data(deal_id)
    q = pi.get_next_question(deal, _answers.get(deal_id, {}))
    return _ok(q)

@preflight_bp.post("/<deal_id>/answer")
def submit_answer(deal_id: str):
    body = request.get_json(silent=True) or {}
    question_id = body.get("question_id", "")
    answer = body.get("answer", "")
    if not question_id or not answer:
        return jsonify({"success": False, "error": "question_id and answer required"}), 400
    _answers.setdefault(deal_id, {})[question_id] = answer
    from services.preflight_interview import PreflightInterview
    pi = PreflightInterview()
    status = pi.completion_status(_answers[deal_id])
    next_q = pi.get_next_question(None, _answers[deal_id])
    return _ok({"status": status, "next_question": next_q})

@preflight_bp.post("/<deal_id>/brainstorm")
def brainstorm(deal_id: str):
    body = request.get_json(silent=True) or {}
    question_id = body.get("question_id", "")
    if not question_id:
        return jsonify({"success": False, "error": "question_id required"}), 400
    from services.preflight_interview import PreflightInterview
    pi = PreflightInterview()
    deal = _get_deal_data(deal_id)
    result = pi.brainstorm(question_id, deal)
    return _ok({"brainstorm": result})

@preflight_bp.post("/<deal_id>/narrative")
def generate_narrative(deal_id: str):
    answers = _answers.get(deal_id, {})
    if not answers:
        return jsonify({"success": False, "error": "No answers submitted yet"}), 400
    from services.preflight_interview import PreflightInterview
    pi = PreflightInterview()
    deal = _get_deal_data(deal_id)
    narrative = pi.generate_deal_narrative(answers, deal)
    status = pi.completion_status(answers)
    return _ok({"narrative": narrative, "status": status})

@preflight_bp.get("/<deal_id>/status")
def interview_status(deal_id: str):
    from services.preflight_interview import PreflightInterview
    pi = PreflightInterview()
    status = pi.completion_status(_answers.get(deal_id, {}))
    return _ok(status)

def _get_deal_data(deal_id: str) -> dict:
    from routes.doc_ingestion import _deal_financials
    return _deal_financials.get(deal_id, {})
