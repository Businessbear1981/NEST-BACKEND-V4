"""
Document Ingestion Engine — Extracts financial data from uploaded documents.

This is the Roots intelligence layer. When docs are uploaded, this engine:
1. Classifies the document type (audited financials, appraisal, officer cert, proforma, etc.)
2. Extracts key financial metrics relevant to bond underwriting
3. Populates the deal record with extracted data
4. Identifies what's missing for the credit memo and rating submission

Document types recognized:
- Audited financial statements (balance sheet, income statement, cash flows)
- Appraisal / feasibility study (property value, unit count, market data)
- Officer's certificate (covenant compliance, DSCR, days cash)
- Proforma / projections (forward-looking financials)
- Sources & uses schedule
- Capital stack / term sheet
- Quality of earnings report (M&A deals)
- Environmental / Phase I
- Market study

Each document type has specific fields to extract.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

from agents._claude import complete


# ── Document Classification ───────────────────────────────────

DOCUMENT_TYPES = {
    "audited_financials": {
        "keywords": ["independent auditors report", "balance sheet", "statement of operations",
                      "statement of cash flows", "notes to financial statements", "GAAP"],
        "extract_fields": [
            "revenue", "ebitda", "net_income", "total_assets", "total_debt",
            "cash_and_equivalents", "total_equity", "depreciation_amortization",
            "interest_expense", "operating_expenses", "current_ratio",
            "accounts_receivable", "accounts_payable", "working_capital",
        ],
    },
    "appraisal": {
        "keywords": ["appraisal report", "market value", "appraised value",
                      "highest and best use", "comparable sales", "HealthTrust"],
        "extract_fields": [
            "appraised_value", "property_type", "unit_count", "unit_mix",
            "occupancy_pct", "entrance_fee_avg", "monthly_fee_avg",
            "land_area_acres", "building_sf", "year_built",
            "market_occupancy", "cap_rate",
        ],
    },
    "officer_certificate": {
        "keywords": ["officer's certificate", "covenant compliance", "debt service coverage",
                      "days cash on hand", "continuing covenant agreement", "bondholder representative"],
        "extract_fields": [
            "dscr", "dscr_series_a", "days_cash_on_hand", "debt_yield",
            "annual_debt_service", "funds_available_for_debt_service",
            "total_outstanding_principal", "covenant_compliance_status",
        ],
    },
    "proforma": {
        "keywords": ["projection", "forecast", "pro forma", "budget",
                      "projected revenue", "projected expenses"],
        "extract_fields": [
            "projected_revenue", "projected_ebitda", "projected_noi",
            "projected_dscr", "projected_occupancy", "stabilization_date",
            "construction_completion_date",
        ],
    },
    "sources_and_uses": {
        "keywords": ["sources and uses", "sources of funds", "uses of funds",
                      "bond proceeds", "equity contribution"],
        "extract_fields": [
            "total_sources", "bond_proceeds", "equity_contribution",
            "total_uses", "acquisition_cost", "construction_cost",
            "reserves", "issuance_costs", "working_capital",
        ],
    },
    "quality_of_earnings": {
        "keywords": ["quality of earnings", "QofE", "adjusted EBITDA",
                      "normalization adjustments", "earnings quality"],
        "extract_fields": [
            "reported_ebitda", "adjusted_ebitda", "adjustments",
            "normalized_working_capital", "run_rate_ebitda",
            "quality_of_revenue", "customer_concentration",
        ],
    },
    "capital_stack": {
        "keywords": ["capital structure", "capital stack", "term sheet",
                      "senior debt", "subordinate", "mezzanine", "equity"],
        "extract_fields": [
            "senior_debt", "subordinate_debt", "mezzanine",
            "equity", "total_capitalization", "ltv", "ltc",
        ],
    },
}

CLASSIFY_PROMPT = """You are a document classifier for NEST Advisors, a digital investment bank.

Given the first few pages of a document, classify it into exactly ONE of these types:
- audited_financials
- appraisal
- officer_certificate
- proforma
- sources_and_uses
- quality_of_earnings
- capital_stack
- other

Return ONLY the type name, nothing else."""

EXTRACT_PROMPT = """You are a financial data extraction engine for NEST Advisors.

Given document text and a list of fields to extract, return a JSON object with the extracted values.
For dollar amounts, return as numbers (no $ or commas).
For percentages, return as decimals (e.g., 0.92 not 92%).
For ratios, return as numbers (e.g., 1.87 not 1.87x).
If a field cannot be found, use null.

Fields to extract: {fields}

Return ONLY the JSON object, no explanation."""


class DocIngestionEngine:
    """Extracts financial data from uploaded documents."""

    def classify(self, text: str) -> str:
        """Classify a document by type based on content."""
        text_lower = text[:5000].lower()

        # Quick keyword matching first
        scores = {}
        for doc_type, config in DOCUMENT_TYPES.items():
            score = sum(1 for kw in config["keywords"] if kw.lower() in text_lower)
            if score > 0:
                scores[doc_type] = score

        if scores:
            return max(scores, key=scores.get)

        # Fall back to AI classification
        response = complete(CLASSIFY_PROMPT, text[:3000], max_tokens=50)
        clean = response.strip().lower().replace('"', '').replace("'", "")
        if clean in DOCUMENT_TYPES:
            return clean
        return "other"

    def extract(self, text: str, doc_type: str = None) -> dict:
        """Extract financial data from document text.

        If doc_type not provided, classifies first.
        Returns extracted fields + metadata.
        """
        if not doc_type:
            doc_type = self.classify(text)

        config = DOCUMENT_TYPES.get(doc_type, {})
        fields = config.get("extract_fields", [])

        if not fields:
            return {
                "doc_type": doc_type,
                "extracted": {},
                "note": "Unknown document type — no fields to extract",
            }

        # Use Claude to extract structured data
        prompt = EXTRACT_PROMPT.format(fields=", ".join(fields))
        response = complete(prompt, text[:15000], max_tokens=2048)

        # Parse JSON response
        try:
            import json
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                clean = clean.rsplit("```", 1)[0]
            extracted = json.loads(clean)
        except Exception:
            extracted = {"parse_error": True, "raw": response[:500]}

        return {
            "doc_type": doc_type,
            "extracted": extracted,
            "fields_requested": fields,
            "fields_found": [k for k, v in extracted.items() if v is not None] if isinstance(extracted, dict) else [],
            "fields_missing": [f for f in fields if isinstance(extracted, dict) and extracted.get(f) is None] if isinstance(extracted, dict) else fields,
            "extracted_at": datetime.utcnow().isoformat(),
        }

    def extract_from_officer_cert(self, text: str) -> dict:
        """Specialized extraction for officer's certificates / covenant compliance.

        These have very structured data — DSCR, days cash, debt yield —
        that can often be extracted with regex before falling back to AI.
        """
        import re

        result = {}

        # DSCR patterns
        dscr_match = re.search(r'Debt Service Coverage Ratio[^0-9]*([0-9]+\.[0-9]+)x?', text, re.IGNORECASE)
        if dscr_match:
            result["dscr"] = float(dscr_match.group(1))

        # Days cash on hand
        dcoh_match = re.search(r'Days Cash on Hand[^0-9]*(\d+)', text, re.IGNORECASE)
        if dcoh_match:
            result["days_cash_on_hand"] = int(dcoh_match.group(1))

        # Debt yield
        dy_match = re.search(r'Debt Yield[^0-9]*(\d+)%', text, re.IGNORECASE)
        if dy_match:
            result["debt_yield"] = float(dy_match.group(1)) / 100

        # Funds available for debt service — handle $ X,XXX,XXX and $ XX,XXX,XXX patterns
        fads_match = re.search(r'Funds Available for Debt Service[^0-9$]*\$?\s*([0-9][0-9, ]+[0-9])', text, re.IGNORECASE)
        if fads_match:
            result["funds_available_for_debt_service"] = float(fads_match.group(1).replace(",", "").replace(" ", ""))

        # Annual debt service
        ads_match = re.search(r'Annual Debt Service[^0-9$]*(?:All Bonds)?\s*\$?\s*([0-9][0-9, ]+[0-9])', text, re.IGNORECASE)
        if ads_match:
            result["annual_debt_service"] = float(ads_match.group(1).replace(",", "").replace(" ", ""))

        # Outstanding principal
        principal_match = re.search(r'(?:Outstanding|Total).*Principal[^0-9$]*\$?\s*([0-9][0-9, ]+[0-9])', text, re.IGNORECASE)
        if principal_match:
            result["total_outstanding_principal"] = float(principal_match.group(1).replace(",", "").replace(" ", ""))

        # Required thresholds
        req_dscr = re.search(r'Required.*Debt Service Coverage[^0-9]*([0-9]+\.[0-9]+)x?', text, re.IGNORECASE)
        if req_dscr:
            result["required_dscr"] = float(req_dscr.group(1))

        req_dcoh = re.search(r'Required.*Days Cash[^0-9]*(\d+)', text, re.IGNORECASE)
        if req_dcoh:
            result["required_days_cash"] = int(req_dcoh.group(1))

        req_dy = re.search(r'Required.*Debt Yield[^0-9]*(\d+)%', text, re.IGNORECASE)
        if req_dy:
            result["required_debt_yield"] = float(req_dy.group(1)) / 100

        # Occupancy
        occ_match = re.search(r'TOTAL.*OCCUPANCY\s+\d+\s+[\d.]+\s+([\d.]+)%', text, re.IGNORECASE)
        if occ_match:
            result["occupancy_pct"] = float(occ_match.group(1)) / 100

        # Upfront fee data (CCRCs)
        upfront_match = re.search(r'Gross Upfront Receipts[^$]*\$\s*([0-9,]+)', text, re.IGNORECASE)
        if upfront_match:
            result["gross_entrance_fee_receipts"] = float(upfront_match.group(1).replace(",", ""))

        refund_match = re.search(r'Refunds Paid[^$]*\$\s*\(?([0-9,]+)\)?', text, re.IGNORECASE)
        if refund_match:
            result["entrance_fee_refunds"] = float(refund_match.group(1).replace(",", ""))

        units_sold_match = re.search(r'Unit Sales\s+(\d+)\s+Units', text, re.IGNORECASE)
        if units_sold_match:
            result["units_sold"] = int(units_sold_match.group(1))

        avg_fee_match = re.search(r'Avg.*Upfront Fee[^$]*\$\s*([0-9,]+)', text, re.IGNORECASE)
        if avg_fee_match:
            result["avg_entrance_fee"] = float(avg_fee_match.group(1).replace(",", ""))

        return {
            "doc_type": "officer_certificate",
            "extracted": result,
            "extraction_method": "regex",
            "fields_found": list(result.keys()),
        }

    def build_deal_from_docs(self, extractions: list[dict]) -> dict:
        """Combine extractions from multiple documents into a single deal record.

        Takes the best available data from each document type.
        Priority: officer_certificate > audited_financials > proforma > appraisal
        """
        deal = {}

        for ext in extractions:
            doc_type = ext.get("doc_type", "")
            data = ext.get("extracted", {})

            if doc_type == "officer_certificate":
                # Highest priority for compliance metrics
                deal.update({k: v for k, v in data.items() if v is not None})

            elif doc_type == "audited_financials":
                # Fill in what officer cert didn't have
                for k, v in data.items():
                    if v is not None and k not in deal:
                        deal[k] = v

            elif doc_type == "appraisal":
                # Property-specific data
                for k in ["appraised_value", "unit_count", "unit_mix", "occupancy_pct",
                           "entrance_fee_avg", "land_area_acres", "cap_rate"]:
                    if data.get(k) is not None:
                        deal[k] = data[k]

            elif doc_type == "proforma":
                # Forward-looking — prefix with projected_
                for k, v in data.items():
                    if v is not None:
                        deal[f"projected_{k}" if not k.startswith("projected_") else k] = v

            elif doc_type == "sources_and_uses":
                deal["sources_and_uses"] = data

            elif doc_type == "quality_of_earnings":
                deal["qoe"] = data
                if data.get("adjusted_ebitda"):
                    deal["ebitda"] = data["adjusted_ebitda"]

        # Compute derived metrics if not already present
        if deal.get("funds_available_for_debt_service") and deal.get("annual_debt_service"):
            if "dscr" not in deal:
                deal["dscr"] = round(deal["funds_available_for_debt_service"] / deal["annual_debt_service"], 2)

        if deal.get("funds_available_for_debt_service") and deal.get("total_outstanding_principal"):
            if "debt_yield" not in deal:
                deal["debt_yield"] = round(deal["funds_available_for_debt_service"] / deal["total_outstanding_principal"], 4)

        deal["_ingestion_timestamp"] = datetime.utcnow().isoformat()
        deal["_documents_ingested"] = len(extractions)
        deal["_document_types"] = [e.get("doc_type") for e in extractions]

        return deal
