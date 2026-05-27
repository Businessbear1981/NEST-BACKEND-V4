"""
Document Ingestion API — upload triggers extraction → results stored in deal.

Flow:
1. Client uploads document to a deal
2. Bernard classifies it and runs extraction
3. Extracted financials stored in deal record
4. Client sees what was extracted + what's still missing
5. When all required docs are in, deal auto-advances to credit stage
"""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

doc_ingestion_bp = Blueprint("doc_ingestion", __name__)


def _ok(data):
    return jsonify({"success": True, "data": data, "error": None, "timestamp": datetime.utcnow().isoformat()})


# In-memory store for extracted deal data (Supabase in production)
_deal_extractions: dict[str, list] = {}
_deal_financials: dict[str, dict] = {}


@doc_ingestion_bp.post("/<deal_id>/ingest")
def ingest_document(deal_id: str):
    """Upload document text for a deal — triggers classification + extraction.

    Body: { text: "document content", filename: "optional.pdf" }
    Returns: classified type, extracted fields, what's still missing.
    Bernard narrates the results.
    """
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    filename = body.get("filename", "uploaded_document")

    if not text:
        return jsonify({"success": False, "error": "text required"}), 400

    from services.doc_ingestion import DocIngestionEngine
    engine = DocIngestionEngine()

    # Classify and extract
    doc_type = engine.classify(text)

    # Extract entity info from EVERY document (address, company, parcel, CUSIP)
    entity_info = engine.extract_entity_info(text)

    # Use specialized extractors by document type
    if doc_type == "officer_certificate":
        extraction = engine.extract_from_officer_cert(text)
    elif doc_type == "appraisal":
        extraction = engine.extract_property_intelligence(text)
    else:
        extraction = engine.extract(text, doc_type)

    # Merge entity info into extraction
    extraction.setdefault("extracted", {}).update({"_entity": entity_info})

    extraction["filename"] = filename
    extraction["deal_id"] = deal_id

    # Store extraction
    _deal_extractions.setdefault(deal_id, []).append(extraction)

    # Rebuild combined deal financials from all docs
    combined = engine.build_deal_from_docs(_deal_extractions[deal_id])
    _deal_financials[deal_id] = combined

    # Check completeness
    from services.rating_benchmarks import REQUIRED_FINANCIAL_DATA
    coverage = _check_completeness(combined)

    # Bernard narration
    narration = None
    try:
        bernard = current_app.config.get("BERNARD")
        if bernard:
            narration = bernard.narrate(
                f"Document ingested: {filename} classified as {doc_type}. "
                f"Extracted {len(extraction.get('fields_found', []))} fields. "
                f"Deal data completeness: {coverage['completeness_pct']}%. "
                f"Missing: {', '.join(coverage['critical_missing'][:5]) if coverage['critical_missing'] else 'none'}.",
                {"deal_id": deal_id, "doc_type": doc_type}
            )
    except Exception:
        pass

    return _ok({
        "document": {
            "filename": filename,
            "type": doc_type,
            "fields_extracted": extraction.get("fields_found", []),
            "fields_missing": extraction.get("fields_missing", []),
        },
        "deal_financials": combined,
        "completeness": coverage,
        "bernard_narration": narration,
        "documents_ingested": len(_deal_extractions.get(deal_id, [])),
    })


@doc_ingestion_bp.get("/<deal_id>/financials")
def get_deal_financials(deal_id: str):
    """Get the combined financial data extracted from all documents for a deal."""
    combined = _deal_financials.get(deal_id, {})
    extractions = _deal_extractions.get(deal_id, [])
    coverage = _check_completeness(combined)

    return _ok({
        "deal_id": deal_id,
        "financials": combined,
        "completeness": coverage,
        "documents": [
            {"filename": e.get("filename"), "type": e.get("doc_type"), "fields": len(e.get("fields_found", []))}
            for e in extractions
        ],
    })


@doc_ingestion_bp.get("/<deal_id>/missing")
def get_missing_data(deal_id: str):
    """Show what financial data is still needed for this deal."""
    combined = _deal_financials.get(deal_id, {})
    coverage = _check_completeness(combined)
    return _ok(coverage)


@doc_ingestion_bp.post("/<deal_id>/run-pipeline")
def run_pipeline_from_docs(deal_id: str):
    """Once docs are ingested, run the deal through the full pipeline.

    Uses extracted financials as inputs to the intelligence engine.
    """
    combined = _deal_financials.get(deal_id, {})
    if not combined:
        return jsonify({"success": False, "error": "No documents ingested for this deal"}), 400

    from services.deal_flow import DealFlow
    flow = DealFlow()
    result = flow.run_full_pipeline(combined)

    return _ok(result)


def _check_completeness(financials: dict) -> dict:
    """Check what percentage of required financial data we have."""
    critical_fields = [
        "revenue", "ebitda", "dscr", "total_debt", "cash_and_equivalents",
        "interest_expense", "annual_debt_service", "total_assets",
    ]
    important_fields = [
        "days_cash_on_hand", "debt_yield", "occupancy_pct",
        "depreciation_amortization", "net_income", "total_equity",
        "funds_available_for_debt_service", "total_outstanding_principal",
    ]

    critical_found = [f for f in critical_fields if financials.get(f) is not None]
    critical_missing = [f for f in critical_fields if financials.get(f) is None]
    important_found = [f for f in important_fields if financials.get(f) is not None]
    important_missing = [f for f in important_fields if financials.get(f) is None]

    total = len(critical_fields) + len(important_fields)
    found = len(critical_found) + len(important_found)

    return {
        "completeness_pct": round(found / total * 100) if total else 0,
        "critical_found": critical_found,
        "critical_missing": critical_missing,
        "important_found": important_found,
        "important_missing": important_missing,
        "ready_for_credit": len(critical_missing) == 0,
        "ready_for_rating": len(critical_missing) == 0 and len(important_missing) <= 3,
    }
