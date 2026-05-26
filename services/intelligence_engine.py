"""
NEST Intelligence Engine — Bond sizing, underwriting, structuring, pricing.

Implements the math from the Operating Framework + Use Case Manual Ch.1.
Each use case (M&A, Construction, Working Capital, Equipment, Real Estate)
follows the six-layer template but with different parameters.

This engine is the core product — it takes deal inputs and produces
a fully structured bond with sizing, pricing, covenants, and reserves.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


# ── NAICS-Driven Sector Intelligence ─────────────────────────

SECTOR_MULTIPLES = {
    "software_saas": {"range": (8, 15), "metric": "EBITDA", "alt_metric": "ARR", "alt_range": (4, 10)},
    "healthcare_services": {"range": (8, 14), "metric": "EBITDA"},
    "business_services": {"range": (6, 10), "metric": "EBITDA"},
    "industrial_manufacturing": {"range": (6, 9), "metric": "EBITDA"},
    "distribution": {"range": (6, 8), "metric": "EBITDA"},
    "consumer_products": {"range": (8, 12), "metric": "EBITDA"},
    "trucking_logistics": {"range": (4, 6), "metric": "EBITDA"},
    "specialty_contractors": {"range": (5, 7), "metric": "EBITDA"},
    "energy_services": {"range": (4, 7), "metric": "EBITDA"},
    "financial_services": {"range": (8, 12), "metric": "EBITDA"},
    "senior_living": {"range": (8, 12), "metric": "EBITDA"},
    "hospitality": {"range": (8, 12), "metric": "EBITDA"},
    "data_centers": {"range": (12, 20), "metric": "EBITDA"},
    "real_estate": {"range": (10, 16), "metric": "NOI", "cap_rate_range": (5.0, 8.0)},
}

SECTOR_LEVERAGE_CAPACITY = {
    "software_saas": {"senior": 4.0, "total": 6.5, "quality": "high"},
    "healthcare_services": {"senior": 4.0, "total": 6.5, "quality": "high"},
    "business_services": {"senior": 3.5, "total": 5.5, "quality": "mid"},
    "industrial_manufacturing": {"senior": 3.5, "total": 5.5, "quality": "mid"},
    "distribution": {"senior": 3.0, "total": 5.0, "quality": "mid"},
    "consumer_products": {"senior": 3.5, "total": 5.5, "quality": "mid"},
    "trucking_logistics": {"senior": 2.5, "total": 4.0, "quality": "low"},
    "specialty_contractors": {"senior": 2.5, "total": 4.5, "quality": "low"},
    "energy_services": {"senior": 2.5, "total": 4.0, "quality": "low"},
    "financial_services": {"senior": 4.0, "total": 6.0, "quality": "high"},
    "senior_living": {"senior": 3.5, "total": 5.5, "quality": "mid"},
    "hospitality": {"senior": 3.0, "total": 5.0, "quality": "mid"},
    "data_centers": {"senior": 4.5, "total": 7.0, "quality": "high"},
    "real_estate": {"senior": 3.5, "total": 5.5, "quality": "mid"},
}

# ── Universal Credit Policy (Appendix F) ─────────────────────

UNIVERSAL_CREDIT_POLICY = {
    "sponsor_standards": {
        "min_experience_years_new_construction": 7,
        "min_experience_years_stabilized": 3,
        "kyc_aml_required": True,
        "ofac_screening_required": True,
        "pep_screening_required": True,
        "max_default_lookback_years": 5,
        "tax_filings_current_required": True,
    },
    "financial_standards": {
        "min_dscr_universal_floor": 1.20,
        "min_debt_yield_universal_floor": 0.08,
        "max_leverage_universal_ceiling": 0.80,
        "min_equity_contribution_universal_floor": 0.20,
        "dsrf_default": "MADS",
        "operating_reserve_months": 3,
    },
    "structural_standards": {
        "security_position": "first_lien",
        "maturity_range_tax_exempt": (20, 30),
        "maturity_range_taxable": (5, 30),
        "covenant_minimums": ["dscr", "additional_bonds_test", "distribution_restrictions", "reporting"],
        "cash_sweep_trigger_dscr": 1.20,
    },
    "exception_authority": {
        "minor": "Senior Credit Underwriter Agent approves with documentation",
        "moderate": "CCO + founders escalation",
        "material": "Founders explicit approval required",
    },
}

# ── Pricing Benchmarks ───────────────────────────────────────

PRICING_BENCHMARKS = {
    "AAA": {"spread_bps": (20, 50), "coupon_range": (3.50, 4.50)},
    "AA": {"spread_bps": (40, 80), "coupon_range": (4.00, 5.00)},
    "A": {"spread_bps": (80, 140), "coupon_range": (4.50, 5.75)},
    "BBB": {"spread_bps": (130, 220), "coupon_range": (5.25, 6.75)},
    "BB": {"spread_bps": (250, 400), "coupon_range": (7.00, 9.00)},
    "B": {"spread_bps": (400, 650), "coupon_range": (8.50, 11.00)},
}

# ── Fee Architecture ─────────────────────────────────────────

FEE_SCHEDULE = {
    "structuring_fee_pct": (0.02, 0.03),
    "placement_fee_pct": (0.005, 0.01),
    "ongoing_admin_fee_bps": (50, 75),
    "commitment_fee_bps": (25, 50),
}


class IntelligenceEngine:
    """Core bond intelligence — sizing, underwriting, structuring, pricing."""

    # ── M&A Acquisition Bond Sizing (Ch.1) ────────────────────

    def size_ma_acquisition(self, inputs: dict) -> dict:
        """Size an M&A acquisition bond per Use Case Manual Ch.1.

        Required inputs:
            ebitda: float — trailing 12-month adjusted EBITDA
            sector: str — sector key from SECTOR_MULTIPLES
            acquisition_multiple: float — agreed EV/EBITDA multiple
            sponsor_equity_pct: float — sponsor equity as % of EV (default 0.30)
            rollover_equity: float — rollover equity amount (default 0)
            seller_note: float — seller financing amount (default 0)
            net_debt_at_close: float — target's existing debt being refinanced (default 0)
            transaction_expenses: float — legal, accounting, advisory (default 0)
            working_capital_cushion: float — additional WC (default 0)
        """
        ebitda = inputs.get("ebitda", 0)
        sector = inputs.get("sector", "business_services")
        mult = inputs.get("acquisition_multiple", 0)
        sponsor_pct = inputs.get("sponsor_equity_pct", 0.30)
        rollover = inputs.get("rollover_equity", 0)
        seller_note = inputs.get("seller_note", 0)
        net_debt = inputs.get("net_debt_at_close", 0)
        tx_expenses = inputs.get("transaction_expenses", 0)
        wc_cushion = inputs.get("working_capital_cushion", 0)

        # Validate sector
        sector_data = SECTOR_MULTIPLES.get(sector, SECTOR_MULTIPLES["business_services"])
        leverage_data = SECTOR_LEVERAGE_CAPACITY.get(sector, SECTOR_LEVERAGE_CAPACITY["business_services"])

        # Enterprise value
        ev = ebitda * mult
        equity_value = ev - net_debt

        # Senior leverage capacity
        senior_leverage = leverage_data["senior"]
        max_senior_bond = ebitda * senior_leverage

        # Sponsor equity check
        sponsor_equity = ev * sponsor_pct

        # Bond sizing = EV - sponsor equity - rollover - seller note
        bond_needed = ev - sponsor_equity - rollover - seller_note
        bond_amount = min(bond_needed, max_senior_bond)

        # Total leverage
        total_leverage = (bond_amount + seller_note) / ebitda if ebitda else 0

        # Reserves
        annual_debt_service = bond_amount * 0.085  # estimated at indicative coupon
        dsrf = annual_debt_service  # MADS
        cap_i_reserve = annual_debt_service * 1.5  # 18 months IO
        closing_reserves = dsrf + cap_i_reserve

        # Cost of issuance
        coi = bond_amount * 0.025

        # Sources and Uses
        total_sources = bond_amount + seller_note + sponsor_equity + rollover
        total_uses = equity_value + net_debt + tx_expenses + closing_reserves + coi + wc_cushion

        # Balance check — adjust bond if needed
        gap = total_uses - total_sources
        if gap > 0:
            bond_amount += gap
            total_sources += gap

        sources = {
            "senior_bond": round(bond_amount),
            "seller_note": round(seller_note),
            "sponsor_equity": round(sponsor_equity),
            "rollover_equity": round(rollover),
            "total": round(total_sources),
        }

        uses = {
            "equity_purchase_price": round(equity_value),
            "debt_refinancing": round(net_debt),
            "transaction_expenses": round(tx_expenses),
            "closing_reserves": round(closing_reserves),
            "cost_of_issuance": round(coi),
            "working_capital_cushion": round(wc_cushion),
            "total": round(total_uses),
        }

        # Credit assessment
        dscr = ebitda / annual_debt_service if annual_debt_service else 0
        credit_grade = self._grade_credit(dscr, total_leverage)

        # Pricing
        pricing = PRICING_BENCHMARKS.get(credit_grade, PRICING_BENCHMARKS["BB"])

        return {
            "use_case": "ma_acquisition",
            "sector": sector,
            "sector_quality": leverage_data["quality"],
            "valuation": {
                "ebitda": ebitda,
                "multiple": mult,
                "sector_multiple_range": sector_data["range"],
                "multiple_in_range": sector_data["range"][0] <= mult <= sector_data["range"][1],
                "enterprise_value": round(ev),
                "equity_value": round(equity_value),
            },
            "capital_structure": {
                "senior_bond": round(bond_amount),
                "senior_leverage": round(bond_amount / ebitda, 2) if ebitda else 0,
                "max_senior_leverage": senior_leverage,
                "total_leverage": round(total_leverage, 2),
                "max_total_leverage": leverage_data["total"],
                "leverage_headroom": round(leverage_data["total"] - total_leverage, 2),
                "equity_pct_of_ev": round(sponsor_pct * 100, 1),
            },
            "sources_and_uses": {"sources": sources, "uses": uses, "balanced": abs(total_sources - total_uses) < 1},
            "bond_structure": {
                "type": "taxable_senior_secured",
                "principal": round(bond_amount),
                "tenor_years": 7,
                "coupon_range": pricing["coupon_range"],
                "spread_range_bps": pricing["spread_bps"],
                "amortization": "18mo_io_then_1pct_annual_then_bullet",
                "call_schedule": {"nc_years": 3, "step_down_premium": True, "par_call_after_year": 5},
            },
            "reserves": {
                "dsrf": round(dsrf),
                "dsrf_type": "MADS",
                "cap_i_reserve": round(cap_i_reserve),
                "cap_i_months": 18,
            },
            "credit": {
                "dscr": round(dscr, 2),
                "grade": credit_grade,
                "meets_universal_floor": dscr >= UNIVERSAL_CREDIT_POLICY["financial_standards"]["min_dscr_universal_floor"],
            },
            "fees": {
                "structuring_fee": round(bond_amount * 0.025),
                "structuring_fee_pct": 2.5,
                "placement_fee": round(bond_amount * 0.0075),
                "placement_fee_pct": 0.75,
                "ongoing_admin_bps": 62.5,
            },
            "readiness_flags": self._ma_readiness_flags(inputs, dscr, total_leverage, leverage_data),
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ── Universal Bond Sizing ─────────────────────────────────

    def size_bond(self, inputs: dict) -> dict:
        """Size a bond for any use case based on deal type."""
        deal_type = inputs.get("deal_type", "ma_acquisition")
        if deal_type == "ma_acquisition":
            return self.size_ma_acquisition(inputs)
        elif deal_type == "construction":
            return self._size_construction(inputs)
        elif deal_type == "working_capital":
            return self._size_working_capital(inputs)
        elif deal_type == "equipment":
            return self._size_equipment(inputs)
        elif deal_type == "real_estate":
            return self._size_real_estate(inputs)
        return {"error": f"Unknown deal type: {deal_type}"}

    def _size_construction(self, inputs: dict) -> dict:
        """Construction & Development bond sizing (Ch.2 template — spec pending)."""
        tpc = inputs.get("total_project_cost", 0)
        ltc = inputs.get("ltc_ratio", 0.75)
        bond_amount = tpc * ltc
        equity = tpc - bond_amount
        return {
            "use_case": "construction",
            "total_project_cost": tpc,
            "bond_amount": round(bond_amount),
            "ltc_ratio": ltc,
            "equity_required": round(equity),
            "amortization": "interest_only_during_construction_then_level_debt_service",
            "note": "Full spec pending Use Case Manual Ch.2",
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _size_working_capital(self, inputs: dict) -> dict:
        """Working Capital bond sizing (Ch.3 template — spec pending)."""
        revenue = inputs.get("annual_revenue", 0)
        wc_pct = inputs.get("wc_pct_revenue", 0.15)
        bond_amount = revenue * wc_pct
        return {
            "use_case": "working_capital",
            "annual_revenue": revenue,
            "bond_amount": round(bond_amount),
            "wc_pct_revenue": wc_pct,
            "structure": "revolving_or_term",
            "note": "Full spec pending Use Case Manual Ch.3",
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _size_equipment(self, inputs: dict) -> dict:
        """Equipment bond sizing (Ch.4 template — spec pending)."""
        equipment_cost = inputs.get("equipment_cost", 0)
        ltv = inputs.get("ltv_ratio", 0.80)
        useful_life = inputs.get("useful_life_years", 7)
        bond_amount = equipment_cost * ltv
        return {
            "use_case": "equipment",
            "equipment_cost": equipment_cost,
            "bond_amount": round(bond_amount),
            "ltv_ratio": ltv,
            "tenor_years": useful_life,
            "amortization": "straight_line_matched_to_depreciation",
            "note": "Full spec pending Use Case Manual Ch.4",
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _size_real_estate(self, inputs: dict) -> dict:
        """Real Estate Acquisition & Stabilization bond sizing (Ch.5 template — spec pending)."""
        noi = inputs.get("noi", 0)
        cap_rate = inputs.get("cap_rate", 0.065)
        ltv = inputs.get("ltv_ratio", 0.70)
        property_value = noi / cap_rate if cap_rate else 0
        bond_amount = property_value * ltv
        dscr = noi / (bond_amount * 0.06) if bond_amount else 0  # estimated at 6% coupon
        return {
            "use_case": "real_estate",
            "noi": noi,
            "cap_rate": cap_rate,
            "property_value": round(property_value),
            "bond_amount": round(bond_amount),
            "ltv_ratio": ltv,
            "estimated_dscr": round(dscr, 2),
            "amortization": "level_debt_service_30yr",
            "note": "Full spec pending Use Case Manual Ch.5",
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ── Underwriting Assessment ───────────────────────────────

    def underwrite(self, deal: dict) -> dict:
        """Run Universal Credit Policy against a deal."""
        policy = UNIVERSAL_CREDIT_POLICY
        flags = []

        dscr = deal.get("dscr", 0)
        leverage = deal.get("total_leverage", 0)
        equity_pct = deal.get("equity_pct", 0)
        sponsor_experience = deal.get("sponsor_experience_years", 0)
        deal_type = deal.get("deal_type", "stabilized")

        min_exp = policy["sponsor_standards"]["min_experience_years_new_construction"] if deal_type == "construction" else policy["sponsor_standards"]["min_experience_years_stabilized"]

        if dscr < policy["financial_standards"]["min_dscr_universal_floor"]:
            flags.append({"field": "dscr", "value": dscr, "threshold": 1.20, "severity": "material", "message": f"DSCR {dscr:.2f}x below universal floor of 1.20x"})

        if leverage > 1 / policy["financial_standards"]["min_equity_contribution_universal_floor"]:
            flags.append({"field": "leverage", "value": leverage, "threshold": 5.0, "severity": "moderate", "message": f"Total leverage {leverage:.1f}x exceeds implied ceiling"})

        if equity_pct < policy["financial_standards"]["min_equity_contribution_universal_floor"]:
            flags.append({"field": "equity_pct", "value": equity_pct, "threshold": 0.20, "severity": "material", "message": f"Equity contribution {equity_pct:.0%} below 20% floor"})

        if sponsor_experience < min_exp:
            flags.append({"field": "sponsor_experience", "value": sponsor_experience, "threshold": min_exp, "severity": "moderate", "message": f"Sponsor experience {sponsor_experience}yr below {min_exp}yr minimum"})

        passed = all(f["severity"] != "material" for f in flags)

        return {
            "passed": passed,
            "flags": flags,
            "flag_count": len(flags),
            "material_flags": sum(1 for f in flags if f["severity"] == "material"),
            "exception_required": not passed,
            "exception_authority": policy["exception_authority"]["material"] if not passed else None,
        }

    # ── Credit Grading ────────────────────────────────────────

    def _grade_credit(self, dscr: float, leverage: float) -> str:
        """Grade credit per JPMorgan benchmarks + Operating Framework."""
        if dscr >= 2.0 and leverage < 2.5:
            return "A"
        elif dscr >= 1.75 and leverage < 3.5:
            return "BBB"
        elif dscr >= 1.50 and leverage < 4.5:
            return "BBB"
        elif dscr >= 1.20 and leverage < 5.5:
            return "BB"
        elif dscr >= 1.10 and leverage < 6.5:
            return "B"
        return "B"

    # ── M&A Readiness Flags ───────────────────────────────────

    def _ma_readiness_flags(self, inputs: dict, dscr: float, leverage: float, leverage_data: dict) -> list[dict]:
        """Acquirer Readiness Checklist per Use Case Manual Ch.1 Section 3.3."""
        flags = []

        if leverage > leverage_data["total"]:
            flags.append({"check": "leverage_capacity", "status": "fail", "message": f"Total leverage {leverage:.1f}x exceeds sector maximum {leverage_data['total']}x"})
        else:
            flags.append({"check": "leverage_capacity", "status": "pass", "message": f"Leverage {leverage:.1f}x within sector capacity {leverage_data['total']}x"})

        equity_pct = inputs.get("sponsor_equity_pct", 0)
        if equity_pct < 0.25:
            flags.append({"check": "equity_contribution", "status": "fail", "message": f"Sponsor equity {equity_pct:.0%} below 25% minimum"})
        else:
            flags.append({"check": "equity_contribution", "status": "pass", "message": f"Sponsor equity {equity_pct:.0%} meets 25% minimum"})

        if dscr < 1.20:
            flags.append({"check": "dscr_floor", "status": "fail", "message": f"DSCR {dscr:.2f}x below 1.20x universal floor"})
        else:
            flags.append({"check": "dscr_floor", "status": "pass", "message": f"DSCR {dscr:.2f}x meets 1.20x floor"})

        mult = inputs.get("acquisition_multiple", 0)
        sector = inputs.get("sector", "business_services")
        sector_range = SECTOR_MULTIPLES.get(sector, {}).get("range", (0, 99))
        if mult > sector_range[1]:
            flags.append({"check": "valuation", "status": "warn", "message": f"Multiple {mult}x above sector range ({sector_range[0]}-{sector_range[1]}x)"})
        else:
            flags.append({"check": "valuation", "status": "pass", "message": f"Multiple {mult}x within sector range"})

        return flags

    # ── Covenant Package Builder ──────────────────────────────

    def build_covenant_package(self, deal_type: str, credit_grade: str, sector: str) -> dict:
        """Build a covenant package based on deal type, credit grade, and sector."""
        base_dscr = {"A": 1.25, "BBB": 1.20, "BB": 1.15, "B": 1.10}.get(credit_grade, 1.20)

        package = {
            "dscr_covenant": base_dscr,
            "additional_bonds_test": f"{base_dscr}x historical, {base_dscr - 0.10:.2f}x projected",
            "restricted_payments": "standard" if credit_grade in ("A", "BBB") else "tight",
            "distribution_trap_dscr": base_dscr - 0.10,
            "reporting": {
                "annual_audited": True,
                "quarterly_unaudited": True,
                "emma_continuing_disclosure": True,
                "material_event_notice": True,
            },
        }

        if deal_type == "ma_acquisition":
            package["acquisition_coverage_test"] = {
                "max_pro_forma_leverage": 5.5,
                "min_fixed_charge_coverage": 2.0,
                "equity_contribution_required": True,
            }
            package["permitted_acquisition_basket"] = "same sector, <$25M individually"
            package["change_of_control_put"] = 101
            package["integration_covenant_holiday_months"] = 18

        elif deal_type == "construction":
            package["construction_completion_deadline"] = True
            package["cost_overrun_reserve"] = "5% of hard costs"
            package["capitalized_interest_reserve"] = True

        return package
