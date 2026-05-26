"""
NEST NightVision Compliance Engine.
Real rule-based compliance checking for institutional bond deals.
SEC, FINRA/MSRB, BSA/AML, State Licensing, Tax — every check matters.

This is the compliance layer for $78M-$231M municipal/private bond deals.
No hardcoded pass/warn. Every status is computed from deal data.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import re
import uuid


# ── SEVERITY LEVELS ──────────────────────────────────────────────
CRITICAL = "critical"   # Blocks deal progression — must resolve
HIGH     = "high"       # Serious risk — resolve before closing
MEDIUM   = "medium"     # Needs attention — resolve before pricing
LOW      = "low"        # Advisory — track and document

# ── STATUS VALUES ────────────────────────────────────────────────
PASS    = "pass"
WARN    = "warn"
FAIL    = "fail"
PENDING = "pending"

# ── THRESHOLDS ───────────────────────────────────────────────────
SAR_THRESHOLD_USD          = 10_000
CTR_THRESHOLD_USD          = 10_000
PRIVATE_ACTIVITY_CAP_USD   = 110_000_000  # typical state volume cap
REG_D_FILING_DAYS          = 15
FORM_D_AMENDMENT_DAYS      = 30
MSRB_G37_CONTRIBUTION_CAP  = 250  # per official per election
ARBITRAGE_REBATE_YIELD_BPS = 10   # de minimis threshold


# ── STATE LICENSING REQUIREMENTS ─────────────────────────────────
STATE_REQUIREMENTS = {
    "FL": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": False, "senior_living_license": "AHCA",
            "environmental_phase1": True, "securities_exemption": "Section 517.051"},
    "TX": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": False, "senior_living_license": "HHSC",
            "environmental_phase1": True, "securities_exemption": "Section 4005.011"},
    "CA": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": False, "senior_living_license": "CDSS/CCL",
            "environmental_phase1": True, "securities_exemption": "Corp Code 25102(f)"},
    "AZ": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": True, "senior_living_license": "ADHS",
            "environmental_phase1": True, "securities_exemption": "ARS 44-1844"},
    "WA": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": True, "senior_living_license": "DSHS",
            "environmental_phase1": True, "securities_exemption": "RCW 21.20.310"},
    "NY": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": True, "senior_living_license": "DOH",
            "environmental_phase1": True, "securities_exemption": "Martin Act exemption"},
    "IL": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": True, "senior_living_license": "IDPH",
            "environmental_phase1": True, "securities_exemption": "815 ILCS 5/4"},
    "PA": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": False, "senior_living_license": "DOH",
            "environmental_phase1": True, "securities_exemption": "70 PS 1-602(b)"},
    "GA": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": True, "senior_living_license": "DCH",
            "environmental_phase1": True, "securities_exemption": "O.C.G.A. 10-5-9"},
    "NC": {"bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
            "con_required": True, "senior_living_license": "DHHS",
            "environmental_phase1": True, "securities_exemption": "GS 78A-17"},
}

# Default for unlisted states
DEFAULT_STATE_REQS = {
    "bd_registration": True, "ia_registration": True, "blue_sky_notice": True,
    "con_required": False, "senior_living_license": "State DOH",
    "environmental_phase1": True, "securities_exemption": "Check state statute",
}


def _check(check_id: str, category: str, name: str, description: str,
           status: str, severity: str, notes: str = "") -> Dict[str, Any]:
    """Build a single compliance check result."""
    return {
        "id": check_id,
        "category": category,
        "name": name,
        "description": description,
        "status": status,
        "severity": severity,
        "checked_at": datetime.utcnow().isoformat(),
        "notes": notes,
    }


# ═══════════════════════════════════════════════════════════════════
# SEC CHECKS
# ═══════════════════════════════════════════════════════════════════

def _run_sec_checks(deal: Dict) -> List[Dict]:
    """SEC securities law compliance checks."""
    checks = []
    deal_type = deal.get("deal_type", "").upper()
    amount = deal.get("amount_usd", 0)
    offering_type = deal.get("offering_type", "").upper()
    is_municipal = deal_type in ("MUNICIPAL", "REVENUE_BOND", "GO_BOND", "CONDUIT")
    is_private = offering_type in ("REG_D", "506B", "506C", "PRIVATE_PLACEMENT")
    form_d_filed = deal.get("form_d_filed", False)
    form_d_date = deal.get("form_d_date")
    first_sale_date = deal.get("first_sale_date")
    blue_sky_states = deal.get("blue_sky_states_filed", [])
    target_states = deal.get("target_states", [])
    has_ppm = deal.get("has_ppm", False)
    ppm_reviewed = deal.get("ppm_reviewed", False)
    accredited_only = deal.get("accredited_investors_only", True)
    general_solicitation = deal.get("general_solicitation", False)
    num_non_accredited = deal.get("non_accredited_investor_count", 0)

    # 1. Rule 15c2-12 — Continuing disclosure (municipal bonds >$1M)
    if is_municipal and amount > 1_000_000:
        has_cdua = deal.get("continuing_disclosure_agreement", False)
        prior_violations = deal.get("prior_cd_violations", 0)
        if has_cdua and prior_violations == 0:
            status = PASS
            notes = "Continuing disclosure undertaking in place. No prior violations."
        elif has_cdua and prior_violations > 0:
            status = WARN
            notes = f"CDUA exists but {prior_violations} prior violation(s) detected. Disclosure in OS required."
        else:
            status = FAIL
            notes = "Missing continuing disclosure undertaking. Required under Rule 15c2-12 for offerings >$1M."
        checks.append(_check("sec_15c2_12", "sec", "Rule 15c2-12 Continuing Disclosure",
                             "Continuing disclosure agreement for municipal securities >$1M",
                             status, CRITICAL, notes))

    # 2. Reg D Exemption (private placements)
    if is_private:
        if offering_type == "506C":
            if accredited_only and deal.get("accredited_verification_method"):
                status = PASS
                notes = f"506(c) — accredited verification via {deal.get('accredited_verification_method')}."
            elif accredited_only and not deal.get("accredited_verification_method"):
                status = FAIL
                notes = "506(c) requires reasonable steps to verify accredited status. No verification method documented."
            else:
                status = FAIL
                notes = "506(c) permits ONLY accredited investors. Non-accredited investors detected."
            checks.append(_check("sec_reg_d_506c", "sec", "Reg D 506(c) Compliance",
                                 "Accredited investor verification under 506(c)",
                                 status, CRITICAL, notes))
        elif offering_type in ("506B", "REG_D"):
            if num_non_accredited <= 35:
                status = PASS if num_non_accredited == 0 else WARN
                notes = (f"506(b) — {num_non_accredited} non-accredited investor(s). "
                         f"{'All accredited.' if num_non_accredited == 0 else 'Max 35 allowed. Ensure sophistication test met.'}")
            else:
                status = FAIL
                notes = f"506(b) permits max 35 non-accredited investors. Count: {num_non_accredited}."
            checks.append(_check("sec_reg_d_506b", "sec", "Reg D 506(b) Compliance",
                                 "Non-accredited investor limits under 506(b)",
                                 status, CRITICAL, notes))
            if general_solicitation:
                checks.append(_check("sec_506b_no_gs", "sec", "506(b) General Solicitation Ban",
                                     "506(b) prohibits general solicitation/advertising",
                                     FAIL, CRITICAL,
                                     "General solicitation detected. 506(b) prohibits this. Switch to 506(c) or cease advertising."))

    # 3. Form D Filing
    if is_private:
        if form_d_filed:
            if first_sale_date and form_d_date:
                sale_dt = _parse_date(first_sale_date)
                filing_dt = _parse_date(form_d_date)
                if sale_dt and filing_dt:
                    days_gap = (filing_dt - sale_dt).days
                    if days_gap <= REG_D_FILING_DAYS:
                        status = PASS
                        notes = f"Form D filed {days_gap} day(s) after first sale. Within 15-day window."
                    else:
                        status = WARN
                        notes = f"Form D filed {days_gap} days after first sale. Exceeds 15-day requirement. Late filing risk."
                else:
                    status = WARN
                    notes = "Form D filed but date verification inconclusive. Confirm filing date."
            else:
                status = PASS
                notes = "Form D filed. Sale date not yet established."
        else:
            if first_sale_date:
                status = FAIL
                notes = "First sale completed but Form D not filed. Must file within 15 days of first sale."
            else:
                status = PENDING
                notes = "Form D not yet filed. Required within 15 days of first sale."
        checks.append(_check("sec_form_d", "sec", "Form D Filing",
                             "SEC Form D filing within 15 days of first sale",
                             status, HIGH, notes))

    # 4. Blue Sky Compliance
    if target_states:
        missing_states = [s for s in target_states if s not in blue_sky_states]
        if not missing_states:
            status = PASS
            notes = f"Blue sky filings complete in all {len(target_states)} target state(s): {', '.join(target_states)}."
        elif len(missing_states) < len(target_states):
            status = WARN
            notes = f"Blue sky filings missing in {len(missing_states)} state(s): {', '.join(missing_states)}. Complete before offering in those states."
        else:
            status = FAIL
            notes = f"No blue sky filings completed. Missing: {', '.join(missing_states)}."
        checks.append(_check("sec_blue_sky", "sec", "Blue Sky State Compliance",
                             "State securities notice filings in all target jurisdictions",
                             status, HIGH, notes))

    # 5. PPM / Anti-fraud
    if is_private:
        if has_ppm and ppm_reviewed:
            status = PASS
            notes = "PPM exists and has been reviewed by securities counsel."
        elif has_ppm and not ppm_reviewed:
            status = WARN
            notes = "PPM exists but has not been reviewed by securities counsel. Review required before distribution."
        else:
            status = FAIL
            notes = "No Private Placement Memorandum. Required for Reg D offerings to satisfy anti-fraud provisions."
        checks.append(_check("sec_ppm", "sec", "PPM Anti-Fraud Disclosure",
                             "Private Placement Memorandum with adequate risk disclosures",
                             status, CRITICAL, notes))

    # If no SEC checks triggered (e.g., missing deal_type), add a pending check
    if not checks:
        checks.append(_check("sec_general", "sec", "SEC Compliance — Incomplete Data",
                             "Insufficient deal data to evaluate SEC compliance",
                             PENDING, HIGH,
                             "Provide deal_type, offering_type, and amount_usd to run SEC checks."))

    return checks


# ═══════════════════════════════════════════════════════════════════
# FINRA / MSRB CHECKS
# ═══════════════════════════════════════════════════════════════════

def _run_finra_checks(deal: Dict) -> List[Dict]:
    """FINRA and MSRB rule compliance checks."""
    checks = []
    deal_type = deal.get("deal_type", "").upper()
    is_municipal = deal_type in ("MUNICIPAL", "REVENUE_BOND", "GO_BOND", "CONDUIT")
    participants = deal.get("participants", {})
    underwriter = participants.get("underwriter", {})
    placement_agent = participants.get("placement_agent", {})
    political_contributions = deal.get("political_contributions", [])
    has_official_statement = deal.get("has_official_statement", False)
    os_reviewed = deal.get("official_statement_reviewed", False)
    fair_dealing_disclosure = deal.get("fair_dealing_disclosure", False)
    amount = deal.get("amount_usd", 0)

    # 1. MSRB G-17 Fair Dealing (municipal)
    if is_municipal:
        if fair_dealing_disclosure:
            status = PASS
            notes = "G-17 fair dealing disclosures delivered to issuer."
        else:
            status = FAIL
            notes = ("MSRB Rule G-17 requires underwriters to make written disclosures to issuers "
                     "about financial risks, conflicts of interest, and compensation. Not documented.")
        checks.append(_check("finra_g17", "finra", "MSRB Rule G-17 Fair Dealing",
                             "Written fair dealing disclosures to municipal issuer",
                             status, CRITICAL, notes))

    # 2. MSRB G-32 Disclosures (municipal)
    if is_municipal:
        if has_official_statement and os_reviewed:
            status = PASS
            notes = "Official Statement prepared and reviewed. G-32 EMMA submission path clear."
        elif has_official_statement and not os_reviewed:
            status = WARN
            notes = "Official Statement drafted but not yet reviewed. Must submit to EMMA within 1 business day of closing."
        else:
            status = FAIL if amount > 1_000_000 else PENDING
            notes = ("No Official Statement prepared. MSRB Rule G-32 requires delivery to EMMA "
                     "within 1 business day of closing for offerings >$1M.")
        checks.append(_check("finra_g32", "finra", "MSRB Rule G-32 Disclosures",
                             "Official Statement preparation and EMMA submission",
                             status, CRITICAL if amount > 1_000_000 else HIGH, notes))

    # 3. MSRB G-37 Political Contributions (municipal)
    if is_municipal:
        blocked = False
        flagged_contributions = []
        for contrib in political_contributions:
            amount_contrib = contrib.get("amount_usd", 0)
            official_role = contrib.get("role", "").lower()
            if amount_contrib > MSRB_G37_CONTRIBUTION_CAP:
                blocked = True
                flagged_contributions.append(
                    f"{contrib.get('contributor', 'Unknown')}: ${amount_contrib:,.0f} to {contrib.get('official', 'unknown official')}")
            elif "executive" in official_role or "partner" in official_role:
                if amount_contrib > MSRB_G37_CONTRIBUTION_CAP:
                    blocked = True
                    flagged_contributions.append(
                        f"{contrib.get('contributor', 'Unknown')} ({official_role}): ${amount_contrib:,.0f}")

        if not political_contributions:
            status = PASS
            notes = "No political contributions reported. G-37 clean."
        elif not blocked:
            status = PASS
            notes = f"All {len(political_contributions)} contribution(s) within G-37 limits ($250 per official per election)."
        else:
            status = FAIL
            notes = (f"G-37 violation — {len(flagged_contributions)} contribution(s) exceed $250 limit. "
                     f"2-year ban on municipal securities business with affected issuers. "
                     f"Flagged: {'; '.join(flagged_contributions)}")
        checks.append(_check("finra_g37", "finra", "MSRB Rule G-37 Political Contributions",
                             "Political contribution limits for municipal underwriters ($250/official/election)",
                             status, CRITICAL if blocked else LOW, notes))

    # 4. Broker-Dealer Registration
    bd_registered = (underwriter.get("finra_registered", False) or
                     placement_agent.get("finra_registered", False) or
                     deal.get("bd_registered", False))
    if bd_registered:
        status = PASS
        crd = underwriter.get("crd_number") or placement_agent.get("crd_number", "")
        notes = f"FINRA-registered broker-dealer confirmed.{f' CRD #{crd}.' if crd else ''}"
    else:
        status = FAIL
        notes = "No FINRA-registered broker-dealer or placement agent identified. Required for securities distribution."
    checks.append(_check("finra_bd_registration", "finra", "Broker-Dealer Registration",
                         "FINRA-registered B/D or placement agent for securities distribution",
                         status, CRITICAL, notes))

    # 5. Suitability / Reg BI
    suitability_docs = deal.get("suitability_documentation", False)
    if suitability_docs:
        status = PASS
        notes = "Investor suitability/Reg BI documentation in place."
    else:
        status = WARN
        notes = "Suitability/Reg BI documentation not confirmed. Required before investor solicitation."
    checks.append(_check("finra_suitability", "finra", "Suitability / Reg BI",
                         "Investor suitability analysis and Reg BI best interest documentation",
                         status, HIGH, notes))

    return checks


# ═══════════════════════════════════════════════════════════════════
# BSA / AML CHECKS
# ═══════════════════════════════════════════════════════════════════

def _run_bsa_aml_checks(deal: Dict) -> List[Dict]:
    """Bank Secrecy Act / Anti-Money Laundering compliance checks."""
    checks = []
    investors = deal.get("investors", [])
    amount = deal.get("amount_usd", 0)
    kyc_complete = deal.get("kyc_complete", False)
    aml_screening_date = deal.get("aml_screening_date")
    beneficial_owners_identified = deal.get("beneficial_owners_identified", False)
    cdd_complete = deal.get("cdd_complete", False)
    sar_procedures = deal.get("sar_procedures_documented", False)
    cash_transactions = deal.get("cash_transactions", [])
    high_risk_jurisdictions = deal.get("high_risk_jurisdictions", [])

    # 1. KYC Verification
    if investors:
        kyc_done = [i for i in investors if i.get("kyc_verified", False)]
        kyc_pending = [i for i in investors if not i.get("kyc_verified", False)]
        if len(kyc_pending) == 0:
            status = PASS
            notes = f"KYC verified for all {len(investors)} investor(s)."
        elif len(kyc_done) > 0:
            status = WARN
            pending_names = [i.get("name", "Unknown") for i in kyc_pending[:5]]
            notes = (f"KYC incomplete: {len(kyc_done)}/{len(investors)} verified. "
                     f"Pending: {', '.join(pending_names)}{'...' if len(kyc_pending) > 5 else ''}.")
        else:
            status = FAIL
            notes = f"No KYC verification completed for {len(investors)} investor(s)."
    elif kyc_complete:
        status = PASS
        notes = "KYC flagged as complete (investor-level detail not provided)."
    else:
        status = PENDING
        notes = "No investor data provided. KYC verification pending."
    checks.append(_check("aml_kyc", "bsa_aml", "KYC Verification",
                         "Know Your Customer identity verification for all investors",
                         status, CRITICAL, notes))

    # 2. SAR Thresholds
    large_cash = [t for t in cash_transactions if t.get("amount_usd", 0) >= SAR_THRESHOLD_USD]
    if cash_transactions:
        if large_cash:
            status = WARN
            notes = (f"{len(large_cash)} cash transaction(s) at/above ${SAR_THRESHOLD_USD:,} threshold. "
                     f"CTR filing required. Review for suspicious activity and potential SAR filing.")
        else:
            status = PASS
            notes = f"All {len(cash_transactions)} cash transaction(s) below reporting thresholds."
    else:
        status = PASS
        notes = "No cash transactions reported. Wire/ACH assumed."
    checks.append(_check("aml_sar", "bsa_aml", "SAR / CTR Thresholds",
                         "Suspicious Activity Report and Currency Transaction Report thresholds",
                         status, HIGH if large_cash else LOW, notes))

    # 3. Beneficial Ownership
    if beneficial_owners_identified:
        status = PASS
        notes = "Beneficial ownership identified for all entities (25%+ owners and one controlling person)."
    elif investors:
        entity_investors = [i for i in investors if i.get("entity_type") in ("LLC", "LP", "CORP", "TRUST")]
        if entity_investors:
            status = FAIL
            notes = (f"{len(entity_investors)} entity investor(s) require beneficial ownership identification "
                     f"under CDD Rule (31 CFR 1010.230). 25%+ equity owners + one control person.")
        else:
            status = PASS
            notes = "All investors are individuals. Beneficial ownership rule applies to entities only."
    else:
        status = PENDING
        notes = "No investor data. Beneficial ownership identification pending."
    checks.append(_check("aml_bo", "bsa_aml", "Beneficial Ownership (CDD Rule)",
                         "Identification of 25%+ equity owners and controlling persons for entity investors",
                         status, CRITICAL, notes))

    # 4. Customer Due Diligence
    if cdd_complete:
        status = PASS
        notes = "Enhanced customer due diligence completed."
    elif high_risk_jurisdictions:
        status = FAIL
        notes = (f"CDD incomplete. High-risk jurisdiction(s) detected: {', '.join(high_risk_jurisdictions)}. "
                 f"Enhanced due diligence required under BSA/AML.")
    elif amount >= 50_000_000:
        status = WARN
        notes = f"Deal size ${amount/1e6:.0f}M warrants enhanced CDD. Not yet completed."
    else:
        status = PENDING
        notes = "Customer due diligence not yet completed."
    checks.append(_check("aml_cdd", "bsa_aml", "Customer Due Diligence (CDD)",
                         "Standard and enhanced customer due diligence procedures",
                         status, HIGH, notes))

    # 5. OFAC / Sanctions Screening
    if aml_screening_date:
        screening_dt = _parse_date(aml_screening_date)
        if screening_dt:
            age_days = (datetime.utcnow() - screening_dt).days
            if age_days <= 30:
                status = PASS
                notes = f"OFAC/SDN screening completed {age_days} day(s) ago. Current."
            elif age_days <= 90:
                status = WARN
                notes = f"OFAC/SDN screening is {age_days} days old. Re-screen recommended (best practice: within 30 days of closing)."
            else:
                status = FAIL
                notes = f"OFAC/SDN screening is {age_days} days stale. Must re-screen before closing."
        else:
            status = WARN
            notes = "Screening date provided but could not be verified."
    else:
        status = FAIL
        notes = "No OFAC/SDN/sanctions screening documented. Required before any securities transaction."
    checks.append(_check("aml_ofac", "bsa_aml", "OFAC / Sanctions Screening",
                         "OFAC SDN list, sectoral sanctions, and non-SDN screening",
                         status, CRITICAL, notes))

    return checks


# ═══════════════════════════════════════════════════════════════════
# STATE LICENSING CHECKS
# ═══════════════════════════════════════════════════════════════════

def _run_state_checks(deal: Dict) -> List[Dict]:
    """State-specific licensing and registration checks."""
    checks = []
    issuer_state = deal.get("issuer_state", "").upper()
    target_states = deal.get("target_states", [])
    all_states = list(set([issuer_state] + [s.upper() for s in target_states])) if issuer_state else [s.upper() for s in target_states]
    project_type = deal.get("project_type", "").lower()
    is_senior_living = "senior" in project_type or "assisted" in project_type or "ccrc" in project_type
    state_licenses_held = deal.get("state_licenses", {})
    environmental_phase1 = deal.get("environmental_phase1_complete", False)
    environmental_phase2 = deal.get("environmental_phase2_complete", False)
    environmental_issues = deal.get("environmental_issues_found", False)

    for state in all_states:
        if not state:
            continue
        reqs = STATE_REQUIREMENTS.get(state, DEFAULT_STATE_REQS)

        # 1. State BD registration
        is_registered = state_licenses_held.get(state, {}).get("bd_registered", False)
        if is_registered:
            status = PASS
            notes = f"Broker-dealer registered in {state}."
        else:
            status = WARN
            notes = f"B/D registration in {state} not confirmed. Required under {reqs.get('securities_exemption', 'state law')}."
        checks.append(_check(f"state_bd_{state.lower()}", "state",
                             f"B/D Registration — {state}",
                             f"Broker-dealer state registration in {state}",
                             status, HIGH, notes))

        # 2. Notice filing / Blue sky
        notice_filed = state_licenses_held.get(state, {}).get("notice_filed", False)
        if notice_filed:
            status = PASS
            notes = f"Notice filing / blue sky exemption filed in {state}."
        else:
            status = WARN
            notes = f"Notice filing not confirmed for {state}. Check exemption under {reqs.get('securities_exemption', 'state statute')}."
        checks.append(_check(f"state_notice_{state.lower()}", "state",
                             f"Notice Filing — {state}",
                             f"State securities notice filing or exemption in {state}",
                             status, MEDIUM, notes))

        # 3. Senior living license (if applicable)
        if is_senior_living:
            has_license = state_licenses_held.get(state, {}).get("senior_living_license", False)
            agency = reqs.get("senior_living_license", "State DOH")
            if state == issuer_state:
                if has_license:
                    status = PASS
                    notes = f"Senior living licensure confirmed with {agency} in {state}."
                else:
                    status = FAIL
                    notes = f"Senior living facility license required from {agency} in {state}. Not documented."
                checks.append(_check(f"state_senior_{state.lower()}", "state",
                                     f"Senior Living License — {state}",
                                     f"State senior living / assisted living facility license in {state} ({agency})",
                                     status, CRITICAL, notes))

            # 4. Certificate of Need (if required)
            if reqs.get("con_required"):
                has_con = state_licenses_held.get(state, {}).get("con_approved", False)
                if has_con:
                    status = PASS
                    notes = f"Certificate of Need approved in {state}."
                else:
                    status = FAIL
                    notes = f"{state} requires Certificate of Need for senior living facilities. Not obtained."
                checks.append(_check(f"state_con_{state.lower()}", "state",
                                     f"Certificate of Need — {state}",
                                     f"State Certificate of Need requirement in {state}",
                                     status, CRITICAL, notes))

    # 5. Environmental compliance (issuer state)
    if environmental_phase1:
        if environmental_issues and not environmental_phase2:
            status = WARN
            notes = "Phase I ESA complete — issues identified. Phase II required but not completed."
        elif environmental_issues and environmental_phase2:
            status = PASS
            notes = "Phase I + Phase II ESA complete. Environmental issues identified and assessed."
        else:
            status = PASS
            notes = "Phase I ESA complete. No recognized environmental conditions identified."
    else:
        status = FAIL
        notes = "Phase I Environmental Site Assessment not completed. Required for bond financing."
    checks.append(_check("state_environmental", "state", "Environmental Compliance",
                         "Phase I/II Environmental Site Assessment (ESA)",
                         status, HIGH, notes))

    if not all_states:
        checks.append(_check("state_general", "state", "State Compliance — No States Identified",
                             "Provide issuer_state and target_states to run state checks",
                             PENDING, HIGH, "No states provided in deal data."))

    return checks


# ═══════════════════════════════════════════════════════════════════
# TAX CHECKS
# ═══════════════════════════════════════════════════════════════════

def _run_tax_checks(deal: Dict) -> List[Dict]:
    """Tax-exempt bond and IRS compliance checks."""
    checks = []
    deal_type = deal.get("deal_type", "").upper()
    amount = deal.get("amount_usd", 0)
    is_tax_exempt = deal.get("tax_exempt", False)
    is_private_activity = deal.get("private_activity_bond", False)
    tax_counsel_opinion = deal.get("tax_counsel_opinion", False)
    arbitrage_certificate = deal.get("arbitrage_certificate", False)
    rebate_analyst_engaged = deal.get("rebate_analyst_engaged", False)
    private_use_pct = deal.get("private_use_pct", 0)
    private_payment_pct = deal.get("private_payment_pct", 0)
    volume_cap_allocation = deal.get("volume_cap_allocation", False)
    is_501c3 = deal.get("is_501c3", False)
    tefra_hearing = deal.get("tefra_hearing_held", False)
    issuer_state = deal.get("issuer_state", "").upper()

    # 1. Tax-exempt status verification
    if is_tax_exempt:
        if tax_counsel_opinion:
            status = PASS
            notes = "Bond counsel tax opinion confirms tax-exempt eligibility."
        else:
            status = WARN
            notes = "Deal marked tax-exempt but no bond counsel tax opinion documented. Required before pricing."
        checks.append(_check("tax_exempt_status", "tax", "Tax-Exempt Status Verification",
                             "Bond counsel opinion confirming tax-exempt eligibility under IRC",
                             status, CRITICAL, notes))

        # TEFRA hearing (required for tax-exempt bonds)
        if tefra_hearing:
            status = PASS
            notes = "TEFRA public hearing held as required."
        else:
            status = FAIL
            notes = "TEFRA public approval hearing not held. Required under IRC Section 147(f) for tax-exempt bonds."
        checks.append(_check("tax_tefra", "tax", "TEFRA Public Hearing",
                             "Tax Equity and Fiscal Responsibility Act public hearing requirement",
                             status, CRITICAL, notes))

    # 2. Private activity bond limits
    if is_tax_exempt:
        # Private business use test: >10% use = private activity bond
        if private_use_pct > 10 or private_payment_pct > 10:
            is_pab = True
        elif is_private_activity:
            is_pab = True
        else:
            is_pab = False

        if is_pab:
            if is_501c3:
                status = PASS
                notes = ("Qualified 501(c)(3) bond — exempt from volume cap under IRC 145. "
                         f"Private use: {private_use_pct}%.")
            elif volume_cap_allocation:
                status = PASS
                notes = (f"Private activity bond with volume cap allocation secured. "
                         f"Amount: ${amount/1e6:.1f}M against state cap.")
            elif amount > PRIVATE_ACTIVITY_CAP_USD:
                status = FAIL
                notes = (f"Private activity bond (${amount/1e6:.1f}M) exceeds typical volume cap "
                         f"(${PRIVATE_ACTIVITY_CAP_USD/1e6:.0f}M). Volume cap allocation not confirmed.")
            else:
                status = WARN
                notes = (f"Private activity bond classification triggered (private use: {private_use_pct}%). "
                         f"Volume cap allocation required but not confirmed.")
            checks.append(_check("tax_pab", "tax", "Private Activity Bond Limits",
                                 "IRC Section 141 private activity bond classification and volume cap",
                                 status, CRITICAL if not volume_cap_allocation and is_pab else MEDIUM, notes))
        else:
            checks.append(_check("tax_pab", "tax", "Private Activity Bond Test",
                                 "IRC Section 141 private business use test",
                                 PASS, LOW,
                                 f"Private use {private_use_pct}% / private payment {private_payment_pct}% — below 10% thresholds. Not a private activity bond."))

    # 3. Arbitrage rebate
    if is_tax_exempt:
        if arbitrage_certificate:
            if rebate_analyst_engaged:
                status = PASS
                notes = "Arbitrage certificate executed. Rebate analyst engaged for ongoing compliance."
            else:
                status = WARN
                notes = "Arbitrage certificate in place but no rebate analyst engaged. Recommend engaging analyst for 5-year computation periods."
        else:
            if amount > 5_000_000:
                status = WARN
                notes = (f"No arbitrage certificate. Required under IRC Section 148 for tax-exempt bonds. "
                         f"Deal size ${amount/1e6:.1f}M — small issuer exception ($5M) does not apply.")
            else:
                status = PASS
                notes = f"Deal size ${amount/1e6:.1f}M may qualify for small issuer exception under IRC 148(f)(4)(D)."
        checks.append(_check("tax_arbitrage", "tax", "Arbitrage Rebate Compliance",
                             "IRC Section 148 arbitrage yield restriction and rebate requirements",
                             status, HIGH, notes))

    # 4. Reissuance / change in use
    if is_tax_exempt and deal.get("refunding", False):
        advance_refunding = deal.get("advance_refunding", False)
        if advance_refunding:
            status = FAIL
            notes = "Advance refunding of tax-exempt bonds prohibited after TCJA 2017. Only current refundings permitted."
        else:
            status = PASS
            notes = "Current refunding — permitted under post-TCJA rules."
        checks.append(_check("tax_refunding", "tax", "Refunding Rules (Post-TCJA)",
                             "Tax Cuts and Jobs Act restrictions on advance refunding",
                             status, CRITICAL if advance_refunding else LOW, notes))

    if not checks:
        if is_tax_exempt:
            checks.append(_check("tax_general", "tax", "Tax Compliance — Incomplete Data",
                                 "Insufficient data for tax compliance analysis",
                                 PENDING, HIGH, "Provide tax_exempt status and deal details."))
        else:
            checks.append(_check("tax_taxable", "tax", "Taxable Bond — Tax Checks Limited",
                                 "Taxable bond — tax-exempt compliance checks not applicable",
                                 PASS, LOW, "Taxable bond. IRC tax-exempt provisions do not apply."))

    return checks


# ═══════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════

def run_compliance_scan(deal_data: Dict) -> Dict[str, Any]:
    """
    Run full compliance scan against deal data.

    Args:
        deal_data: Dict with deal details including:
            - deal_type: MUNICIPAL, REVENUE_BOND, GO_BOND, CONDUIT, CORPORATE, etc.
            - offering_type: REG_D, 506B, 506C, PRIVATE_PLACEMENT, PUBLIC
            - amount_usd: Deal size in USD
            - issuer_state: Two-letter state code
            - target_states: List of state codes for investor solicitation
            - project_type: senior_living, healthcare, infrastructure, etc.
            - participants: {underwriter: {}, placement_agent: {}}
            - investors: [{name, kyc_verified, entity_type}, ...]
            - tax_exempt: bool
            - ... and many more fields per check category

    Returns:
        Structured compliance report with overall score and per-category breakdown.
    """
    scan_id = str(uuid.uuid4())[:12]
    started_at = datetime.utcnow()

    # Run all check categories
    sec_checks = _run_sec_checks(deal_data)
    finra_checks = _run_finra_checks(deal_data)
    bsa_aml_checks = _run_bsa_aml_checks(deal_data)
    state_checks = _run_state_checks(deal_data)
    tax_checks = _run_tax_checks(deal_data)

    all_checks = sec_checks + finra_checks + bsa_aml_checks + state_checks + tax_checks

    # Compute per-category summaries
    categories = {}
    for cat_id, cat_name, cat_checks in [
        ("sec", "SEC / Securities", sec_checks),
        ("finra", "FINRA / MSRB", finra_checks),
        ("bsa_aml", "BSA / AML", bsa_aml_checks),
        ("state", "State Licensing", state_checks),
        ("tax", "Tax / IRS", tax_checks),
    ]:
        total = len(cat_checks)
        passed = sum(1 for c in cat_checks if c["status"] == PASS)
        warned = sum(1 for c in cat_checks if c["status"] == WARN)
        failed = sum(1 for c in cat_checks if c["status"] == FAIL)
        pending = sum(1 for c in cat_checks if c["status"] == PENDING)
        applicable = total - pending
        score = round((passed / applicable) * 100) if applicable > 0 else 0
        categories[cat_id] = {
            "name": cat_name,
            "checks": cat_checks,
            "summary": {
                "total": total,
                "pass": passed,
                "warn": warned,
                "fail": failed,
                "pending": pending,
                "score": score,
            },
        }

    # Overall scoring
    total_checks = len(all_checks)
    total_pass = sum(1 for c in all_checks if c["status"] == PASS)
    total_warn = sum(1 for c in all_checks if c["status"] == WARN)
    total_fail = sum(1 for c in all_checks if c["status"] == FAIL)
    total_pending = sum(1 for c in all_checks if c["status"] == PENDING)
    applicable = total_checks - total_pending
    overall_score = round((total_pass / applicable) * 100) if applicable > 0 else 0

    # Critical blockers — fail + critical severity
    blockers = [c for c in all_checks if c["status"] == FAIL and c["severity"] == CRITICAL]

    # Deal progression gate
    can_proceed = len(blockers) == 0
    gate_status = "CLEAR" if can_proceed else "BLOCKED"
    if not can_proceed:
        gate_message = f"{len(blockers)} critical blocker(s) must be resolved before deal progression."
    elif total_warn > 0:
        gate_message = f"Clear to proceed with {total_warn} warning(s). Address before closing."
    elif total_pending > 0:
        gate_message = f"Clear to proceed with {total_pending} item(s) pending verification."
    else:
        gate_message = "All compliance checks passed. Deal is clear."

    completed_at = datetime.utcnow()

    return {
        "scan_id": scan_id,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_ms": int((completed_at - started_at).total_seconds() * 1000),
        "deal_summary": {
            "deal_type": deal_data.get("deal_type", "UNKNOWN"),
            "amount_usd": deal_data.get("amount_usd", 0),
            "issuer_state": deal_data.get("issuer_state", ""),
            "project_type": deal_data.get("project_type", ""),
            "tax_exempt": deal_data.get("tax_exempt", False),
        },
        "overall": {
            "score": overall_score,
            "total_checks": total_checks,
            "pass": total_pass,
            "warn": total_warn,
            "fail": total_fail,
            "pending": total_pending,
            "gate_status": gate_status,
            "gate_message": gate_message,
            "can_proceed": can_proceed,
        },
        "blockers": blockers,
        "categories": categories,
    }


def get_check_definitions() -> Dict[str, Any]:
    """Return the full compliance check catalog with categories and descriptions."""
    return {
        "sec": {
            "name": "SEC / Securities",
            "checks": [
                {"id": "sec_15c2_12", "name": "Rule 15c2-12 Continuing Disclosure",
                 "description": "Continuing disclosure agreement for municipal securities >$1M",
                 "applies_to": "Municipal bonds >$1M", "severity": CRITICAL},
                {"id": "sec_reg_d_506c", "name": "Reg D 506(c) Compliance",
                 "description": "Accredited investor verification under 506(c)",
                 "applies_to": "506(c) private placements", "severity": CRITICAL},
                {"id": "sec_reg_d_506b", "name": "Reg D 506(b) Compliance",
                 "description": "Non-accredited investor limits under 506(b)",
                 "applies_to": "506(b) private placements", "severity": CRITICAL},
                {"id": "sec_form_d", "name": "Form D Filing",
                 "description": "SEC Form D filing within 15 days of first sale",
                 "applies_to": "All Reg D offerings", "severity": HIGH},
                {"id": "sec_blue_sky", "name": "Blue Sky State Compliance",
                 "description": "State securities notice filings in all target jurisdictions",
                 "applies_to": "All offerings with multi-state investors", "severity": HIGH},
                {"id": "sec_ppm", "name": "PPM Anti-Fraud Disclosure",
                 "description": "Private Placement Memorandum with adequate risk disclosures",
                 "applies_to": "Private placements", "severity": CRITICAL},
            ],
        },
        "finra": {
            "name": "FINRA / MSRB",
            "checks": [
                {"id": "finra_g17", "name": "MSRB Rule G-17 Fair Dealing",
                 "description": "Written fair dealing disclosures to municipal issuer",
                 "applies_to": "Municipal bond underwriting", "severity": CRITICAL},
                {"id": "finra_g32", "name": "MSRB Rule G-32 Disclosures",
                 "description": "Official Statement preparation and EMMA submission",
                 "applies_to": "Municipal bond offerings >$1M", "severity": CRITICAL},
                {"id": "finra_g37", "name": "MSRB Rule G-37 Political Contributions",
                 "description": "Political contribution limits for municipal underwriters ($250/official/election)",
                 "applies_to": "Municipal securities professionals", "severity": CRITICAL},
                {"id": "finra_bd_registration", "name": "Broker-Dealer Registration",
                 "description": "FINRA-registered B/D or placement agent for securities distribution",
                 "applies_to": "All securities transactions", "severity": CRITICAL},
                {"id": "finra_suitability", "name": "Suitability / Reg BI",
                 "description": "Investor suitability analysis and Reg BI best interest documentation",
                 "applies_to": "All investor solicitation", "severity": HIGH},
            ],
        },
        "bsa_aml": {
            "name": "BSA / AML",
            "checks": [
                {"id": "aml_kyc", "name": "KYC Verification",
                 "description": "Know Your Customer identity verification for all investors",
                 "applies_to": "All investors", "severity": CRITICAL},
                {"id": "aml_sar", "name": "SAR / CTR Thresholds",
                 "description": "Suspicious Activity Report and Currency Transaction Report thresholds",
                 "applies_to": "Cash transactions >= $10,000", "severity": HIGH},
                {"id": "aml_bo", "name": "Beneficial Ownership (CDD Rule)",
                 "description": "Identification of 25%+ equity owners and controlling persons for entity investors",
                 "applies_to": "Entity investors (LLC, LP, Corp, Trust)", "severity": CRITICAL},
                {"id": "aml_cdd", "name": "Customer Due Diligence (CDD)",
                 "description": "Standard and enhanced customer due diligence procedures",
                 "applies_to": "All investors, enhanced for high-risk", "severity": HIGH},
                {"id": "aml_ofac", "name": "OFAC / Sanctions Screening",
                 "description": "OFAC SDN list, sectoral sanctions, and non-SDN screening",
                 "applies_to": "All parties to the transaction", "severity": CRITICAL},
            ],
        },
        "state": {
            "name": "State Licensing",
            "checks": [
                {"id": "state_bd_*", "name": "B/D Registration — [State]",
                 "description": "Broker-dealer state registration (per target state)",
                 "applies_to": "Each state where securities are offered", "severity": HIGH},
                {"id": "state_notice_*", "name": "Notice Filing — [State]",
                 "description": "State securities notice filing or exemption",
                 "applies_to": "Each target state", "severity": MEDIUM},
                {"id": "state_senior_*", "name": "Senior Living License — [State]",
                 "description": "State senior living / assisted living facility license",
                 "applies_to": "Senior living projects in issuer state", "severity": CRITICAL},
                {"id": "state_con_*", "name": "Certificate of Need — [State]",
                 "description": "State Certificate of Need requirement",
                 "applies_to": "States requiring CON for healthcare facilities", "severity": CRITICAL},
                {"id": "state_environmental", "name": "Environmental Compliance",
                 "description": "Phase I/II Environmental Site Assessment (ESA)",
                 "applies_to": "All bond-financed projects", "severity": HIGH},
            ],
        },
        "tax": {
            "name": "Tax / IRS",
            "checks": [
                {"id": "tax_exempt_status", "name": "Tax-Exempt Status Verification",
                 "description": "Bond counsel opinion confirming tax-exempt eligibility under IRC",
                 "applies_to": "Tax-exempt bonds", "severity": CRITICAL},
                {"id": "tax_tefra", "name": "TEFRA Public Hearing",
                 "description": "Tax Equity and Fiscal Responsibility Act public hearing requirement",
                 "applies_to": "Tax-exempt bonds", "severity": CRITICAL},
                {"id": "tax_pab", "name": "Private Activity Bond Limits",
                 "description": "IRC Section 141 private activity bond classification and volume cap",
                 "applies_to": "Tax-exempt bonds with >10% private use", "severity": CRITICAL},
                {"id": "tax_arbitrage", "name": "Arbitrage Rebate Compliance",
                 "description": "IRC Section 148 arbitrage yield restriction and rebate requirements",
                 "applies_to": "Tax-exempt bonds >$5M", "severity": HIGH},
                {"id": "tax_refunding", "name": "Refunding Rules (Post-TCJA)",
                 "description": "Tax Cuts and Jobs Act restrictions on advance refunding",
                 "applies_to": "Refunding bonds", "severity": CRITICAL},
            ],
        },
    }


# ── HELPERS ──────────────────────────────────────────────────────

def _parse_date(val) -> Optional[datetime]:
    """Parse a date string. Handles ISO 8601 and common formats."""
    if isinstance(val, datetime):
        return val
    if not isinstance(val, str):
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


# ── MODULE-LEVEL INSTANCE ────────────────────────────────────────
# Expose as a simple namespace for import convenience
class ComplianceEngine:
    """Singleton wrapper for compliance engine functions."""
    run_scan = staticmethod(run_compliance_scan)
    get_definitions = staticmethod(get_check_definitions)


compliance_engine = ComplianceEngine()
