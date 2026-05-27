"""Client Portal API — client-facing deal dashboard."""
from datetime import datetime
from flask import Blueprint, jsonify, request

client_portal_bp = Blueprint("client_portal", __name__)

def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})

def _portal():
    from services.client_portal import ClientPortal
    return ClientPortal()

@client_portal_bp.get("/<deal_id>/dashboard")
def dashboard(deal_id: str):
    return _ok(_portal().get_client_dashboard(deal_id))

@client_portal_bp.post("/<deal_id>/questionnaire")
def create_questionnaire(deal_id: str):
    body = request.get_json(silent=True) or {}
    unanswered = body.get("unanswered_questions", [])
    return _ok(_portal().generate_questionnaire(deal_id, unanswered))

@client_portal_bp.post("/<deal_id>/respond")
def submit_response(deal_id: str):
    body = request.get_json(silent=True) or {}
    return _ok(_portal().submit_response(deal_id, body.get("question_id", ""), body.get("response", "")))

@client_portal_bp.post("/<deal_id>/push-doc")
def push_document(deal_id: str):
    body = request.get_json(silent=True) or {}
    return _ok(_portal().push_document_for_review(deal_id, body))

@client_portal_bp.post("/<deal_id>/review/<doc_id>")
def review_doc(deal_id: str, doc_id: str):
    body = request.get_json(silent=True) or {}
    return _ok(_portal().client_review(deal_id, doc_id, body.get("action", "approved"), body.get("notes", "")))

@client_portal_bp.post("/<deal_id>/bernard")
def bernard_chat(deal_id: str):
    body = request.get_json(silent=True) or {}
    message = body.get("message", "")
    if not message:
        return jsonify({"success": False, "error": "message required"}), 400
    return _ok(_portal().client_bernard_chat(deal_id, message))

@client_portal_bp.post("/<deal_id>/email")
def generate_email(deal_id: str):
    body = request.get_json(silent=True) or {}
    return _ok(_portal().generate_email(deal_id, body.get("questionnaire_id", ""), body.get("recipient", {})))
