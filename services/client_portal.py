"""
Client Portal — Two-sided deal platform.

NEST side: works the deal (docs, credit, rating, structuring)
Client side: reviews, answers questions, signs off, talks to Bernard

When the preflight interview has unanswered questions or needs
client input, it generates a client questionnaire. The questionnaire
goes to the client dashboard and optionally via email (Aria agent).

Bernard is available on both sides:
- NEST side: orchestrator, analyst
- Client side: concierge, answers questions about the deal, process, timeline

All client interactions are recorded and flow back to the working deal.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

from agents._claude import complete


# In-memory stores (Supabase in production)
_client_questionnaires: dict[str, list] = {}  # deal_id → list of questionnaires
_client_responses: dict[str, dict] = {}       # deal_id → {question_id: response}
_client_documents: dict[str, list] = {}       # deal_id → docs pending client review
_client_signatures: dict[str, list] = {}      # deal_id → signed items
_client_conversations: dict[str, list] = {}   # deal_id → Bernard chat history


class ClientPortal:
    """Manages the client-facing side of the deal."""

    def generate_questionnaire(self, deal_id: str, unanswered: list[dict], deal: dict = None) -> dict:
        """Generate a client questionnaire from unanswered preflight questions.

        Takes the questions the NEST team couldn't answer and reformats
        them for client consumption — simpler language, context provided,
        grouped by topic.
        """
        questions = []
        for q in unanswered:
            # Rewrite for client audience
            client_version = {
                "id": q["id"],
                "section": q.get("section", "General"),
                "question": q["question"],
                "context": q.get("why", ""),
                "required": True,
                "type": "text",  # text, number, select, file
            }

            # Make certain questions more client-friendly
            if q["id"] == "sponsor_background":
                client_version["question"] = "Please provide background on your organization — years in operation, number of similar projects completed, and key management team members."
            elif q["id"] == "sponsor_financial_capacity":
                client_version["question"] = "Can you confirm your organization's ability to fund the required equity contribution and support any cost overruns if needed?"
            elif q["id"] == "business_description":
                client_version["question"] = "Please describe your project or business in detail — what services you provide, who your customers are, and what makes your operation unique in the market."
            elif q["id"] == "proforma_assumptions":
                client_version["question"] = "Please walk us through the key assumptions in your financial projections — revenue growth rate, expected occupancy at stabilization, and stabilization timeline."

            questions.append(client_version)

        questionnaire = {
            "id": f"questionnaire-{deal_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            "deal_id": deal_id,
            "questions": questions,
            "total_questions": len(questions),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "due_date": None,  # Set by NEST team
        }

        _client_questionnaires.setdefault(deal_id, []).append(questionnaire)
        return questionnaire

    def submit_response(self, deal_id: str, question_id: str, response: str) -> dict:
        """Client submits a response to a questionnaire question.

        Response is recorded and flows back to the working deal's
        preflight answers.
        """
        _client_responses.setdefault(deal_id, {})[question_id] = {
            "response": response,
            "submitted_at": datetime.utcnow().isoformat(),
            "source": "client_portal",
        }

        return {
            "question_id": question_id,
            "recorded": True,
            "total_responses": len(_client_responses[deal_id]),
        }

    def get_client_dashboard(self, deal_id: str) -> dict:
        """Get the client's view of the deal — everything they need to see and do."""
        questionnaires = _client_questionnaires.get(deal_id, [])
        responses = _client_responses.get(deal_id, {})
        pending_docs = _client_documents.get(deal_id, [])
        signatures = _client_signatures.get(deal_id, [])
        conversations = _client_conversations.get(deal_id, [])

        # Calculate pending items
        pending_questions = 0
        for q in questionnaires:
            for question in q.get("questions", []):
                if question["id"] not in responses:
                    pending_questions += 1

        pending_reviews = len([d for d in pending_docs if d.get("status") == "pending_review"])
        pending_sigs = len([s for s in signatures if s.get("status") == "pending"])

        return {
            "deal_id": deal_id,
            "action_items": {
                "questions_pending": pending_questions,
                "documents_to_review": pending_reviews,
                "signatures_needed": pending_sigs,
                "total_pending": pending_questions + pending_reviews + pending_sigs,
            },
            "questionnaires": questionnaires,
            "responses": responses,
            "documents_for_review": pending_docs,
            "signatures": signatures,
            "conversation_count": len(conversations),
        }

    def push_document_for_review(self, deal_id: str, doc: dict) -> dict:
        """Push a document to the client dashboard for review/signature.

        Documents like: credit memo draft, term sheet, engagement letter,
        commitment letter, closing docs.
        """
        item = {
            "id": f"doc-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "deal_id": deal_id,
            "title": doc.get("title", "Document"),
            "type": doc.get("type", "review"),  # review, signature, information
            "content": doc.get("content", ""),
            "status": "pending_review",
            "pushed_at": datetime.utcnow().isoformat(),
            "reviewed_at": None,
            "signed_at": None,
        }
        _client_documents.setdefault(deal_id, []).append(item)
        return item

    def client_review(self, deal_id: str, doc_id: str, action: str, notes: str = "") -> dict:
        """Client reviews a document — approve, request changes, or sign."""
        docs = _client_documents.get(deal_id, [])
        for doc in docs:
            if doc["id"] == doc_id:
                doc["status"] = action  # approved, changes_requested, signed
                doc["reviewed_at"] = datetime.utcnow().isoformat()
                doc["client_notes"] = notes
                if action == "signed":
                    doc["signed_at"] = datetime.utcnow().isoformat()
                    _client_signatures.setdefault(deal_id, []).append({
                        "doc_id": doc_id,
                        "title": doc["title"],
                        "signed_at": doc["signed_at"],
                        "status": "signed",
                    })
                return doc
        return {"error": "Document not found"}

    def client_bernard_chat(self, deal_id: str, message: str) -> dict:
        """Client talks to Bernard on their side.

        Bernard answers questions about the deal, process, timeline,
        what documents are needed, what happens next.
        Records the conversation and feeds relevant info back to the deal.
        """
        # Record message
        _client_conversations.setdefault(deal_id, []).append({
            "role": "client",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Bernard responds in client-friendly mode
        system = """You are Bernard, the concierge for NEST Advisors' client portal.
You're speaking to the borrower/sponsor — the client, not the NEST team.

Your tone: Professional, reassuring, clear. No banking jargon without explanation.
Help them understand: what's happening with their deal, what documents are needed,
what questions they need to answer, what the timeline looks like.

If they provide information about their deal (financials, business details, risk factors),
note it and let them know it will be recorded and sent to the deal team.

If they ask about bond mechanics, explain clearly. If they ask about timeline,
give realistic expectations. If they ask about cost, be transparent about fee structure."""

        response = complete(system, message, max_tokens=2048)

        # Record Bernard's response
        _client_conversations.setdefault(deal_id, []).append({
            "role": "bernard",
            "message": response,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Check if client provided deal-relevant info that should flow back
        info_keywords = ["revenue", "ebitda", "units", "occupancy", "cost", "equity",
                         "timeline", "management", "risk", "competitor"]
        contains_deal_info = any(kw in message.lower() for kw in info_keywords)

        return {
            "response": response,
            "contains_deal_info": contains_deal_info,
            "note": "Information recorded and will be reviewed by the deal team" if contains_deal_info else None,
        }

    def generate_email(self, deal_id: str, questionnaire_id: str, recipient: dict) -> dict:
        """Generate an email to send the questionnaire to the client.

        Uses the Aria outreach agent's format.
        """
        questionnaires = _client_questionnaires.get(deal_id, [])
        q = next((q for q in questionnaires if q["id"] == questionnaire_id), None)
        if not q:
            return {"error": "Questionnaire not found"}

        question_list = "\n".join(
            f"{i+1}. {question['question']}"
            for i, question in enumerate(q["questions"])
        )

        email = {
            "to": recipient.get("email", ""),
            "subject": f"NEST Advisors — Information Request for Your Bond Financing",
            "body": f"""Dear {recipient.get('name', 'Client')},

Thank you for engaging NEST Advisors for your bond financing. We are making good progress on the deal and need some additional information to complete our credit analysis.

Please review and respond to the following questions at your earliest convenience. You can respond directly to this email or log into your client dashboard at [portal link] to submit your responses.

INFORMATION NEEDED:

{question_list}

If you have any questions about what's being asked or why, please reach out to your deal team or use the Bernard assistant in your client portal — he can explain each question in detail and help you think through your responses.

We appreciate your prompt attention to these items as they are needed to advance the credit analysis.

Best regards,
NEST Advisors
Sean Gilmore & Josh Edwards, Co-Founders

---
This is a confidential communication from NEST Advisors.
""",
            "status": "draft",
            "generated_at": datetime.utcnow().isoformat(),
        }
        return email
