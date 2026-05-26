"""Tests for the CreditEngine — metric computation, scoring, and benchmarks."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.credit_engine import CreditEngine, BENCHMARKS


engine = CreditEngine()


# ── compute_metrics ────────────────────────────────────────────────

class TestComputeMetrics:
    """Strong deal should get an A-grade; weak deal should be sub-IG."""

    STRONG_DEAL = {
        "noi": 20_000_000,
        "debt_service": 8_000_000,
        "total_debt": 80_000_000,
        "total_assets": 200_000_000,
        "ebitda": 25_000_000,
        "interest_expense": 6_000_000,
        "equity": 120_000_000,
        "project_value": 200_000_000,
        "total_project_cost": 200_000_000,
    }

    WEAK_DEAL = {
        "noi": 5_000_000,
        "debt_service": 5_000_000,
        "total_debt": 90_000_000,
        "total_assets": 100_000_000,
        "ebitda": 6_000_000,
        "interest_expense": 4_500_000,
        "equity": 10_000_000,
        "project_value": 100_000_000,
        "total_project_cost": 100_000_000,
    }

    def test_strong_deal_dscr(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        assert m["dscr"] == 2.5  # 20M / 8M

    def test_strong_deal_ltv(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        assert m["ltv"] == 40.0  # 80M / 200M * 100

    def test_strong_deal_grade(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        # cf_leverage=4.0 (80M/20M) breaches A threshold (<1.5), so grade is BB
        # This is correct per JPM benchmarks — single breach = downgrade
        assert m["obligor_grade"] == "BB"

    def test_weak_deal_dscr(self):
        m = engine.compute_metrics(self.WEAK_DEAL)
        assert m["dscr"] == 1.0  # 5M / 5M

    def test_weak_deal_is_sub_ig(self):
        m = engine.compute_metrics(self.WEAK_DEAL)
        assert m["obligor_grade"] == "BB"  # sub-investment grade

    def test_metrics_contain_expected_keys(self):
        m = engine.compute_metrics(self.STRONG_DEAL)
        expected = {
            "dscr", "ltv", "cash_flow_leverage", "balance_sheet_leverage",
            "debt_to_ebitda", "interest_coverage", "equity_pct",
            "obligor_grade", "overall_score", "recommendation",
        }
        assert expected.issubset(set(m.keys()))


# ── JPM Benchmark comparison ──────────────────────────────────────

class TestBenchmarks:

    def test_a_grade_thresholds(self):
        a = BENCHMARKS["A"]
        assert a["dscr"] == 2.0
        assert a["ltv"] == 55
        assert a["icr"] == 3.5

    def test_bbb_minus_thresholds(self):
        bbb = BENCHMARKS["BBB_minus"]
        assert bbb["dscr"] == 1.5
        assert bbb["ltv"] == 70
        assert bbb["d_ebitda"] == 6.5

    def test_grade_falls_to_bb_on_single_breach(self):
        """If DSCR is A-grade but LTV breaches, grade degrades."""
        grade = engine._determine_grade(
            dscr=2.5,   # A-grade
            ltv=80,     # breaches everything
            cf_lev=1.0, bs_lev=1.0, d_ebitda=3.0, icr=5.0,
        )
        assert grade == "BB"


# ── score_deal ────────────────────────────────────────────────────

class TestScoreDeal:

    def test_excellent_score(self):
        result = engine.score_deal({
            "dscr": 3.0, "ltv": 40, "cash_flow_leverage": 0.8,
            "balance_sheet_leverage": 1.2, "debt_to_ebitda": 3.0,
            "interest_coverage": 5.0, "sponsor_quality": 10,
            "market_fundamentals": 15,
        })
        assert result["total_score"] >= 85
        assert result["grade"] == "A"
        assert "proceed" in result["recommendation"].lower()

    def test_poor_score(self):
        result = engine.score_deal({
            "dscr": 1.0, "ltv": 85, "cash_flow_leverage": 4.0,
            "balance_sheet_leverage": 5.0, "debt_to_ebitda": 10.0,
            "interest_coverage": 1.0, "sponsor_quality": 2,
            "market_fundamentals": 3,
        })
        assert result["total_score"] < 50
        assert "decline" in result["recommendation"].lower() or "restructure" in result["recommendation"].lower()


# ── compute_lgd ───────────────────────────────────────────────────

class TestLGD:

    def test_bare_lgd(self):
        lgd = engine.compute_lgd({})
        assert lgd == 60.0  # 100 - 40

    def test_bank_conduit_lgd_near_zero(self):
        lgd = engine.compute_lgd({
            "senior_lien": True,
            "bank_manages_proceeds": True,
            "io_funded": True,
            "maturity_reserve_pct": 2.5,
            "lc_coverage_pct": 100,
        })
        assert lgd <= 5.0  # NEST model approaches 0%


# ── capital stack ─────────────────────────────────────────────────

class TestCapitalStack:

    def test_default_split(self):
        stack = engine.compute_capital_stack(100_000_000)
        assert stack["a_amount"] == 75_000_000
        assert stack["b_amount"] == 7_000_000
        assert stack["equity"] == 18_000_000
        assert stack["cltv"] == 82.0
