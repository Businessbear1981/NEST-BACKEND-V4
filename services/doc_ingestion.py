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
    "rent_roll": {
        "keywords": ["rent roll", "unit number", "tenant", "lease expiration",
                      "monthly rent", "move-in date", "unit type", "square feet"],
        "extract_fields": [
            "total_units", "occupied_units", "occupancy_pct",
            "gross_potential_rent", "effective_gross_income",
            "average_rent_per_unit", "average_sf_per_unit",
            "lease_expiration_schedule", "vacancy_loss",
            "concessions", "bad_debt",
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

# ── Entity & Property Identification ──────────────────────────
# These fields are extracted from EVERY document type — not just financials.
# The platform builds the deal identity from whatever docs come in.

ENTITY_FIELDS = [
    "entity_name",           # Convivial Jacaranda Trace, LLC
    "dba_name",              # Jacaranda Trace Retirement Community
    "entity_type",           # LLC, Inc, LP, Trust, Corp
    "state_of_formation",    # Florida
    "tax_status",            # 501(c)(3), for-profit, government
    "ein",                   # Federal EIN if found
    "sponsor_name",          # David Falk, Convivial Life Inc
    "management_company",    # If separate from owner
    "contact_name",          # Joel Anderson, Chad Stutzman
    "contact_title",         # CEO, Board Chair, Manager
    "contact_email",
    "contact_phone",
]

PROPERTY_FIELDS = [
    "property_name",         # Jacaranda Trace Retirement Community
    "property_address",      # 3600 William Penn Way
    "city",                  # Venice
    "state",                 # FL
    "zip_code",              # 34293
    "county",                # Sarasota
    "parcel_number",         # From appraisal or title
    "parcel_ids",            # Multiple parcels
    "legal_description",     # From title/survey
    "campus_acres",
    "building_sf",
    "year_built",
    "zoning",
]

BOND_FIELDS = [
    "cusip",                 # 34061WCA0
    "cusip_list",            # Multiple series
    "series_name",           # Series 2022A
    "issuer_authority",      # Florida LGFC, conduit issuer
    "trustee",               # UMB Bank
    "trustee_contact",       # Kevin Fox
    "bond_counsel",
    "underwriter",           # Ziegler
    "bondholder_rep",        # Deutsche Bank AG
    "indenture_date",
    "closing_date",
    "maturity_date",
    "outstanding_principal",
]

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

    def extract_entity_info(self, text: str) -> dict:
        """Extract entity, property, and bond identifiers from ANY document.

        Runs on every document regardless of type. Pulls addresses,
        company names, parcel numbers, CUSIPs, counterparty names.
        """
        import re
        info = {}

        # Entity names — look for LLC, Inc, LP patterns
        entity = re.search(r'([A-Z][A-Za-z\s&,]+(?:LLC|Inc\.?|LP|L\.P\.|Corp\.?|Trust|Association))', text)
        if entity:
            info["entity_name"] = entity.group(1).strip()

        # DBA / project name
        dba = re.search(r'(?:d/b/a|doing business as|known as|project name)[:\s]+([A-Z][A-Za-z\s]+)', text, re.IGNORECASE)
        if dba:
            info["dba_name"] = dba.group(1).strip()

        # Address — street number + street name + city, state zip
        addr = re.search(r'(\d+\s+[A-Za-z\s]+(?:Way|Street|Road|Drive|Avenue|Boulevard|Circle|Lane|Court|Place|Pkwy|Blvd|St|Rd|Dr|Ave|Ln|Ct|Pl))\s*[,.]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[,.]?\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?', text)
        if addr:
            info["property_address"] = addr.group(1).strip()
            info["city"] = addr.group(2).strip()
            info["state"] = addr.group(3).strip()
            if addr.group(4):
                info["zip_code"] = addr.group(4).strip()

        # Parcel numbers — various formats
        parcel = re.search(r'(?:parcel|folio|APN|assessor|tax\s*(?:id|identification))\s*(?:#|number|no\.?)?\s*[:\s]*([0-9\-\.\/]+)', text, re.IGNORECASE)
        if parcel:
            info["parcel_number"] = parcel.group(1).strip()

        # Multiple parcels
        parcels = re.findall(r'(?:parcel|folio)\s*(?:#|number)?\s*[:\s]*([0-9][0-9\-\.\/]+[0-9])', text, re.IGNORECASE)
        if len(parcels) > 1:
            info["parcel_ids"] = parcels

        # CUSIP
        cusips = re.findall(r'CUSIP\s*#?\s*([A-Z0-9]{9})', text, re.IGNORECASE)
        if cusips:
            info["cusip"] = cusips[0]
            if len(cusips) > 1:
                info["cusip_list"] = cusips

        # Series name
        series = re.findall(r'Series\s+(20\d{2}[A-Z]?)', text)
        if series:
            info["series_names"] = series

        # EIN
        ein = re.search(r'(?:EIN|Employer Identification|Tax ID)\s*[:#]?\s*(\d{2}-\d{7})', text, re.IGNORECASE)
        if ein:
            info["ein"] = ein.group(1)

        # 501(c)(3) status
        if '501(c)(3)' in text or '501c3' in text.lower():
            info["tax_status"] = "501(c)(3)"
        elif 'for-profit' in text.lower() or 'for profit' in text.lower():
            info["tax_status"] = "for_profit"

        # Trustee
        for bank in ["U.S. Bank", "UMB Bank", "BNY Mellon", "Wilmington Trust",
                      "Zions Bank", "Computershare", "Regions", "Truist"]:
            if bank.lower() in text.lower():
                info["trustee"] = bank
                break

        # Trustee contact
        trustee_contact = re.search(r'(?:Dear|Attention|Attn)\s+(?:Mr\.|Ms\.|Mrs\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
        if trustee_contact:
            info["trustee_contact"] = trustee_contact.group(1)

        # Bond counsel
        for firm in ["Orrick", "Hawkins Delafield", "Squire Patton", "Norton Rose",
                      "Kutak Rock", "Chapman and Cutler", "Greenberg Traurig",
                      "Ballard Spahr", "Stradling Yocca"]:
            if firm.lower() in text.lower():
                info["bond_counsel"] = firm
                break

        # Underwriter
        for uw in ["Piper Sandler", "Stifel", "Hilltop", "Raymond James", "RBC",
                    "Ziegler", "B.C. Ziegler", "HJ Sims", "BOK Financial", "Baird",
                    "Janney Montgomery"]:
            if uw.lower() in text.lower():
                info["underwriter"] = uw
                break

        # Bondholder representative
        for rep in ["Deutsche Bank", "Bank of New York", "Wells Fargo"]:
            if rep.lower() in text.lower():
                info["bondholder_rep"] = rep
                break

        # Contact names with titles
        contacts = re.findall(r'(?:Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
        if contacts:
            info["contacts_found"] = list(set(contacts))

        # Dates
        closing = re.search(r'(?:closing date|closed on|dated as of)\s*[:\s]*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if closing:
            info["closing_date"] = closing.group(1)

        # County
        county = re.search(r'([A-Z][a-z]+)\s+County', text)
        if county:
            info["county"] = county.group(1)

        # Acres
        acres = re.search(r'([\d.]+)[- ]?acre', text, re.IGNORECASE)
        if acres:
            info["campus_acres"] = float(acres.group(1))

        return info

    def extract_property_intelligence(self, text: str) -> dict:
        """Specialized extraction for appraisals — builds property intelligence.

        Extracts unit mix, occupancy, property value, campus details,
        fee model, year built, market data — everything needed to
        understand the physical asset and its operating profile.
        """
        import re
        result = {"doc_type": "appraisal", "extraction_method": "property_intelligence"}
        prop = {}

        # Unit counts by care level
        il = re.search(r'(\d+)\s*(?:independent living|IL).*?(?:apartment|unit|residence)', text, re.IGNORECASE)
        if il: prop['il_units'] = int(il.group(1))

        al = re.search(r'(\d+)\s*(?:assisted living|AL).*?(?:apartment|unit)', text, re.IGNORECASE)
        if al: prop['al_units'] = int(al.group(1))

        mc = re.search(r'(\d+)\s*(?:memory (?:care|support)|MC).*?(?:apartment|unit|bed)', text, re.IGNORECASE)
        if mc: prop['mc_units'] = int(mc.group(1))

        snf = re.search(r'(\d+)\s*(?:skilled nursing|SNF).*?(?:bed|unit)', text, re.IGNORECASE)
        if snf: prop['snf_beds'] = int(snf.group(1))

        villas = re.search(r'(\d+)\s*(?:villa|cottage)', text, re.IGNORECASE)
        if villas: prop['villas'] = int(villas.group(1))

        prop['total_units'] = sum(prop.get(k, 0) for k in ['il_units', 'al_units', 'mc_units', 'snf_beds', 'villas'])

        # Campus
        acres = re.search(r'([\d.]+)[- ]?acre', text, re.IGNORECASE)
        if acres: prop['campus_acres'] = float(acres.group(1))

        # Appraised value
        for pattern in [
            r'(?:as.is|market|appraised)\s+(?:market\s+)?value[^$]*\$\s*([\d,]+(?:\.\d+)?)',
            r'value.*(?:conclude|estimate|opinion)[^$]*\$\s*([\d,]+(?:\.\d+)?)',
        ]:
            val = re.search(pattern, text, re.IGNORECASE)
            if val:
                prop['appraised_value'] = float(val.group(1).replace(',', ''))
                break

        # Occupancy
        for level, key in [('independent living|IL', 'il_occupancy_pct'),
                           ('assisted living|AL', 'al_occupancy_pct'),
                           ('memory care|MC', 'mc_occupancy_pct')]:
            occ = re.search(rf'(?:{level}).*?(\d{{2,3}})%', text, re.IGNORECASE)
            if occ: prop[key] = int(occ.group(1)) / 100

        # Overall occupancy
        total_occ = re.search(r'(?:total|overall|average)\s*(?:/\s*average)?\s*occupancy.*?(\d{2,3}(?:\.\d+)?)%', text, re.IGNORECASE)
        if total_occ: prop['occupancy_pct'] = float(total_occ.group(1)) / 100

        # Fee model
        text_lower = text.lower()
        if 'entrance fee' in text_lower or 'entry fee' in text_lower:
            prop['fee_model'] = 'entrance_fee'
        if 'life lease' in text_lower:
            prop['fee_model'] = 'life_lease'
        elif 'rental' in text_lower and 'entrance' not in text_lower:
            prop['fee_model'] = 'rental'

        # Entrance fee amounts
        ef = re.search(r'(?:average|avg|mean)\s*(?:entrance|entry|upfront)\s*fee[^$]*\$\s*([\d,]+)', text, re.IGNORECASE)
        if ef: prop['entrance_fee_avg'] = float(ef.group(1).replace(',', ''))

        # Year built / opened
        yr = re.search(r'(?:open(?:ed|ing)|construct(?:ed|ion)|built|completed)\s*(?:in\s+)?(\d{4})', text, re.IGNORECASE)
        if yr: prop['year_built'] = int(yr.group(1))

        # Most recent expansion
        exp = re.search(r'(?:most recent|latest|last)\s*(?:expansion|phase|addition).*?(\d{4})', text, re.IGNORECASE)
        if exp: prop['last_expansion_year'] = int(exp.group(1))

        # Market data — PMA occupancy
        pma_occ = re.search(r'(?:primary market|PMA).*?occupancy.*?(\d{2,3})%', text, re.IGNORECASE)
        if pma_occ: prop['market_occupancy_pct'] = int(pma_occ.group(1)) / 100

        # Property type classification
        if any(kw in text_lower for kw in ['ccrc', 'continuing care', 'life plan']):
            prop['property_type'] = 'CCRC'
        elif 'senior living' in text_lower:
            prop['property_type'] = 'senior_living'
        elif 'multifamily' in text_lower or 'apartment' in text_lower:
            prop['property_type'] = 'multifamily'
        elif 'hospital' in text_lower:
            prop['property_type'] = 'hospital'

        # Location
        loc = re.search(r'(?:located|situated)\s+(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})', text)
        if loc: prop['location'] = loc.group(1)
        else:
            loc2 = re.search(r'([A-Z][a-z]+),\s*(Florida|Texas|California|New York|Washington|Arizona)', text)
            if loc2: prop['location'] = f"{loc2.group(1)}, {loc2.group(2)}"

        # Appraiser
        for firm in ['HealthTrust', 'Kaufman Hall', 'CliftonLarsonAllen', 'Plante Moran',
                      'CBRE', 'JLL', 'Cushman', 'HVS', 'STR']:
            if firm.lower() in text_lower:
                prop['appraiser'] = firm
                break

        # Condominium structure (relevant for CCRCs)
        if 'condominium' in text_lower:
            prop['condo_structure'] = True

        result['extracted'] = prop
        result['fields_found'] = [k for k, v in prop.items() if v is not None]
        return result

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
                # Property intelligence — builds the physical asset profile
                deal["property"] = data
                for k in ["appraised_value", "occupancy_pct", "entrance_fee_avg",
                           "campus_acres", "cap_rate", "property_type", "fee_model",
                           "location", "year_built", "total_units", "il_units",
                           "al_units", "mc_units", "villas", "condo_structure",
                           "il_occupancy_pct", "al_occupancy_pct", "mc_occupancy_pct",
                           "market_occupancy_pct", "appraiser"]:
                    if data.get(k) is not None:
                        deal[k] = data[k]
                # Compute LTV if we have appraised value and bond amount
                if data.get("appraised_value") and deal.get("bond_amount"):
                    deal["ltv"] = round(deal["bond_amount"] / data["appraised_value"], 4)

            elif doc_type == "rent_roll":
                # Rent roll feeds occupancy and revenue
                deal["rent_roll"] = data
                for k in ["total_units", "occupied_units", "occupancy_pct",
                           "gross_potential_rent", "effective_gross_income",
                           "average_rent_per_unit"]:
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

        # Merge entity info from all documents
        entity = {}
        for ext in extractions:
            ent = ext.get("extracted", {}).get("_entity", {})
            for k, v in ent.items():
                if v and k not in entity:
                    entity[k] = v
        if entity:
            deal["entity"] = entity
            # Promote key fields to deal level
            for k in ["entity_name", "property_address", "city", "state", "zip_code",
                       "county", "parcel_number", "cusip", "cusip_list", "series_names",
                       "trustee", "bond_counsel", "underwriter", "ein", "tax_status",
                       "bondholder_rep"]:
                if entity.get(k) and k not in deal:
                    deal[k] = entity[k]

        deal["_ingestion_timestamp"] = datetime.utcnow().isoformat()
        deal["_documents_ingested"] = len(extractions)
        deal["_document_types"] = [e.get("doc_type") for e in extractions]

        return deal
