"""Tests for the NightVision Compliance Engine — rule-based compliance scanning."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.compliance_engine import (
    run_compliance_scan,
    SAR_THRESHOLD_USD,
    PASS, WARN, FAIL, PENDING,
)


# ── Helpers ────────────────────────────────────────────────────────

def _find_check(result, check_id):
    """Find a specific check by ID across all categories."""
    for cat in result["categories"].values():
        for chk in cat["checks"]:
            if chk["id"] == check_id:
                return chk
    return None


# ── Basic scan structure ──────────────────────────────────────────

class TestScanStructure:

    def test_scan_returns_required_keys(self):
        result = run_compliance_scan({"deal_type": "MUNICIPAL", "amount_usd": 50_000_000})
        assert "scan_id" in result
        assert "overall" in result
        assert "categories" in result
        assert "blockers" in result
        for cat_id in ("sec", "finra", "bsa_aml", "state", "tax"):
            assert cat_id in result["categories"]

    def test_overall_has_scoring_fields(self):
        result = run_compliance_scan({"deal_type": "CORPORATE", "amount_usd": 1_000_000})
        overall = result["overall"]
        for key in ("score", "total_checks", "pass", "warn", "fail", "pending",
                     "gate_status", "can_proceed"):
            assert key in overall


# ── KYC checks ────────────────────────────────────────────────────

class TestKYC:

    def test_missing_kyc_flags_pending(self):
        """No investor data at all should yield pending KYC."""
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "amount_usd": 50_000_000,
        })
        kyc = _find_check(result, "aml_kyc")
        assert kyc is not None
        assert kyc["status"] == PENDING

    def test_incomplete_kyc_flags_warning(self):
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "amount_usd": 50_000_000,
            "investors": [
                {"name": "Fund A", "kyc_verified": True},
                {"name": "Fund B", "kyc_verified": False},
            ],
        })
        kyc = _find_check(result, "aml_kyc")
        assert kyc["status"] == WARN

    def test_all_kyc_verified_passes(self):
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "amount_usd": 50_000_000,
            "investors": [
                {"name": "Fund A", "kyc_verified": True},
                {"name": "Fund B", "kyc_verified": True},
            ],
        })
        kyc = _find_check(result, "aml_kyc")
        assert kyc["status"] == PASS


# ── SAR threshold checks ─────────────────────────────────────────

class TestSARThresholds:

    def test_large_deal_with_cash_transactions_triggers_sar_warning(self):
        """Cash transactions >= $10K should trigger CTR/SAR warning."""
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "amount_usd": 15_000_000,
            "cash_transactions": [
                {"amount_usd": 12_000, "description": "initial deposit"},
            ],
        })
        sar = _find_check(result, "aml_sar")
        assert sar is not None
        assert sar["status"] == WARN
        assert "threshold" in sar["notes"].lower() or "CTR" in sar["notes"]

    def test_no_cash_transactions_passes(self):
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "amount_usd": 15_000_000,
        })
        sar = _find_check(result, "aml_sar")
        assert sar["status"] == PASS

    def test_small_cash_below_threshold_passes(self):
        result = run_compliance_scan({
            "deal_type": "CORPORATE",
            "amount_usd": 5_000_000,
            "cash_transactions": [
                {"amount_usd": 5_000, "description": "petty cash"},
            ],
        })
        sar = _find_check(result, "aml_sar")
        assert sar["status"] == PASS


# ── Clean deal should be unblocked ────────────────────────────────

class TestCleanDeal:

    def test_well_documented_deal_has_no_critical_blockers(self):
        """A fully-documented municipal deal should not be blocked."""
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "offering_type": "506B",
            "amount_usd": 78_000_000,
            "issuer_state": "FL",
            "target_states": ["FL"],
            "project_type": "infrastructure",
            "tax_exempt": True,
            "tax_counsel_opinion": True,
            "tefra_hearing_held": True,
            "arbitrage_certificate": True,
            "rebate_analyst_engaged": True,
            "kyc_complete": True,
            "cdd_complete": True,
            "beneficial_owners_identified": True,
            "aml_screening_date": "2026-05-15",
            "continuing_disclosure_agreement": True,
            "fair_dealing_disclosure": True,
            "has_official_statement": True,
            "official_statement_reviewed": True,
            "bd_registered": True,
            "suitability_documentation": True,
            "form_d_filed": True,
            "has_ppm": True,
            "ppm_reviewed": True,
            "blue_sky_states_filed": ["FL"],
            "accredited_investors_only": True,
            "environmental_phase1_complete": True,
            "state_licenses": {"FL": {"bd_registered": True, "notice_filed": True}},
            "sar_procedures_documented": True,
        })
        # Should be clear or at most warnings — no critical fails
        assert result["overall"]["gate_status"] == "CLEAR"
        assert result["overall"]["can_proceed"] is True


# ── FINRA BD registration ─────────────────────────────────────────

class TestFINRA:

    def test_missing_bd_registration_fails(self):
        result = run_compliance_scan({
            "deal_type": "MUNICIPAL",
            "amount_usd": 50_000_000,
        })
        bd = _find_check(result, "finra_bd_registration")
        assert bd is not None
        assert bd["status"] == FAIL
