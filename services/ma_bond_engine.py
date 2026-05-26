"""
NEST M&A Bond Engine.
Completely separate from construction bonds.
EBITDA $20M+ companies. PE or strategic acquisitions.
PIK, draw-term, B tranche balance sheet optimization.
No P&I = cash stays in business = EBITDA grows = bigger exit.
"""
from datetime import datetime

MA_BOND_RULES = {
    "minimum_ebitda_usd": 20_000_000,
    "typical_bond_size_x_ebitda": (4, 7),
    "a_tranche_pct": 80,
    "b_tranche_pct": 20,
    "a_grade_target": "BBB-",
    "b_grade": "B or BB",
    "pik_available": True,
    "pik_description": "Coupon accretes instead of cash pay. No P&I obligation during hold.",
    "draw_term_structure": True,
    "draw_term_description": "Don't commit 100% at close. Release tranches as pro forma validates.",
    "typical_hold_years": (3, 7),
    "exit_paths": ["strategic_sale", "IPO", "PE_recap", "NEST_second_swing"],
    "b_tranche_balance_sheet": "B tranche held as marketable security. Improves debt-to-book cap.",
    "vs_leveraged_loan": "No P&I kills cash flow. Bond frees cash to build EBITDA. Better balance sheet optics.",
}

NEST_MA_ARRANGEMENT_FEE_PCT = 2.25
NEST_MONITORING_FEE_ANNUAL_PCT = 0.50
NEST_EQUITY_KICKER_PCT = 3.0


class MABondEngine:

    def structure_acquisition_bond(self, company: dict,
                                   acquisition_terms: dict) -> dict:
        ebitda = company.get("ebitda_usd", 0)
        acq_price = acquisition_terms.get("acquisition_price_usd", 0)
        hold_years = acquisition_terms.get("hold_years", 5)
        ebitda_growth = acquisition_terms.get("ebitda_growth_pct", 10)
        exit_multiple = acquisition_terms.get("exit_multiple", 7)

        if ebitda < MA_BOND_RULES["minimum_ebitda_usd"]:
            return {"error": f"EBITDA ${ebitda:,.0f} below ${MA_BOND_RULES['minimum_ebitda_usd']:,.0f} minimum",
                    "minimum_ebitda_usd": MA_BOND_RULES["minimum_ebitda_usd"]}

        leverage_multiple = round(acq_price / ebitda, 1) if ebitda else 0
        total_bond = acq_price
        a_amount = round(total_bond * MA_BOND_RULES["a_tranche_pct"] / 100)
        b_amount = total_bond - a_amount

        a_rate_pct = 7.0
        b_rate_pct = 12.0

        initial_draw_pct = 60
        initial_draw = round(total_bond * initial_draw_pct / 100)
        unreleased = total_bond - initial_draw

        pik_analysis = self.model_pik_vs_cash_pay(total_bond, b_rate_pct, hold_years, ebitda_growth)

        exit_ebitda = round(ebitda * (1 + ebitda_growth / 100) ** hold_years)
        exit_ev = round(exit_ebitda * exit_multiple)
        accreted_bond = round(total_bond * (1 + b_rate_pct / 100 * MA_BOND_RULES["b_tranche_pct"] / 100) ** hold_years)
        equity_at_exit = exit_ev - accreted_bond

        nest_arrangement = round(total_bond * NEST_MA_ARRANGEMENT_FEE_PCT / 100)
        nest_monitoring = round(total_bond * NEST_MONITORING_FEE_ANNUAL_PCT / 100 * hold_years)
        nest_equity_value = round(exit_ev * NEST_EQUITY_KICKER_PCT / 100) if equity_at_exit > 0 else 0

        deleverage = []
        for yr in range(hold_years + 1):
            yr_ebitda = round(ebitda * (1 + ebitda_growth / 100) ** yr)
            yr_debt = total_bond
            deleverage.append({
                "year": yr,
                "ebitda_usd": yr_ebitda,
                "debt_usd": yr_debt,
                "leverage_x": round(yr_debt / yr_ebitda, 2) if yr_ebitda else 0,
                "debt_to_ev_pct": round(yr_debt / (yr_ebitda * exit_multiple) * 100, 1) if yr_ebitda else 0,
            })

        exit_analysis = {}
        for path in MA_BOND_RULES["exit_paths"]:
            mult_needed = round(accreted_bond / exit_ebitda, 1) if exit_ebitda else 0
            if path == "strategic_sale":
                exit_analysis[path] = {"minimum_multiple": mult_needed, "probability": "high" if mult_needed < 6 else "medium",
                                       "nest_equity_usd": nest_equity_value}
            elif path == "IPO":
                exit_analysis[path] = {"minimum_multiple": mult_needed, "probability": "medium",
                                       "nest_equity_usd": nest_equity_value, "lockup_months": 6}
            elif path == "PE_recap":
                exit_analysis[path] = {"minimum_multiple": mult_needed, "probability": "high",
                                       "nest_equity_usd": round(nest_equity_value * 0.7)}
            elif path == "NEST_second_swing":
                exit_analysis[path] = {"minimum_multiple": mult_needed, "unreleased_capital_usd": unreleased,
                                       "bolt_on_capacity_usd": unreleased, "nest_equity_usd": round(nest_equity_value * 1.3)}

        lc = self.lc_capacity_analysis(b_amount, hold_years * 12, exit_ebitda)

        return {
            "company": company.get("name", "Target Co"),
            "ebitda_usd": ebitda,
            "acquisition_price_usd": acq_price,
            "leverage_multiple": leverage_multiple,
            "a_tranche": {
                "amount_usd": a_amount, "pct_of_total": MA_BOND_RULES["a_tranche_pct"],
                "grade": MA_BOND_RULES["a_grade_target"], "rate_pct": a_rate_pct,
                "term_years": hold_years, "call_year": 2, "pik": False,
                "treatment": "senior_secured",
            },
            "b_tranche": {
                "amount_usd": b_amount, "pct_of_total": MA_BOND_RULES["b_tranche_pct"],
                "grade": MA_BOND_RULES["b_grade"], "rate_pct": b_rate_pct,
                "term_years": hold_years, "pik": True,
                "pik_description": MA_BOND_RULES["pik_description"],
                "balance_sheet_treatment": MA_BOND_RULES["b_tranche_balance_sheet"],
            },
            "draw_schedule": self.draw_term_analysis(total_bond, initial_draw_pct,
                                                     [{"month": 12, "ebitda_target_pct": 100},
                                                      {"month": 24, "ebitda_target_pct": 110}]),
            "pik_impact": pik_analysis,
            "deleverage_path": deleverage,
            "exit_analysis": exit_analysis,
            "second_swing_optionality": self.second_swing_analysis(company, unreleased, hold_years),
            "lc_capacity": lc,
            "nest_economics": {
                "arrangement_fee_usd": nest_arrangement,
                "monitoring_fees_usd": nest_monitoring,
                "equity_kicker_usd": nest_equity_value,
                "total_nest_revenue_usd": nest_arrangement + nest_monitoring + nest_equity_value,
                "fee_pct": NEST_MA_ARRANGEMENT_FEE_PCT,
                "equity_pct": NEST_EQUITY_KICKER_PCT,
            },
            "vs_leveraged_loan": MA_BOND_RULES["vs_leveraged_loan"],
        }

    def model_pik_vs_cash_pay(self, bond_amount: float, coupon_pct: float,
                              hold_years: int, ebitda_growth_pct: float) -> dict:
        annual_coupon = round(bond_amount * coupon_pct / 100)

        pik_accreted = bond_amount
        cash_pay_total_paid = 0
        pik_timeline = []
        cash_timeline = []

        for yr in range(1, hold_years + 1):
            pik_accreted = round(pik_accreted * (1 + coupon_pct / 100))
            cash_pay_total_paid += annual_coupon

            pik_timeline.append({"year": yr, "accreted_balance_usd": pik_accreted, "cash_paid_usd": 0,
                                 "cash_retained_usd": annual_coupon * yr})
            cash_timeline.append({"year": yr, "balance_usd": bond_amount, "cash_paid_usd": cash_pay_total_paid,
                                  "cash_retained_usd": 0})

        base_ebitda = bond_amount / 5
        pik_exit_ebitda = round(base_ebitda * (1 + ebitda_growth_pct / 100) ** hold_years)
        cash_growth_drag = ebitda_growth_pct * 0.6
        cash_exit_ebitda = round(base_ebitda * (1 + cash_growth_drag / 100) ** hold_years)

        exit_mult = 7
        pik_exit_ev = round(pik_exit_ebitda * exit_mult)
        cash_exit_ev = round(cash_exit_ebitda * exit_mult)

        pik_equity = pik_exit_ev - pik_accreted
        cash_equity = cash_exit_ev - bond_amount

        return {
            "pik": {
                "timeline": pik_timeline,
                "total_accreted_usd": pik_accreted,
                "cash_paid_during_hold_usd": 0,
                "exit_ebitda_usd": pik_exit_ebitda,
                "exit_ev_usd": pik_exit_ev,
                "equity_at_exit_usd": pik_equity,
            },
            "cash_pay": {
                "timeline": cash_timeline,
                "total_cash_paid_usd": cash_pay_total_paid,
                "exit_ebitda_usd": cash_exit_ebitda,
                "exit_ev_usd": cash_exit_ev,
                "equity_at_exit_usd": cash_equity,
            },
            "pik_advantage_usd": pik_equity - cash_equity,
            "verdict": "PIK wins" if pik_equity > cash_equity else "Cash pay wins",
            "explanation": "PIK retains cash in business. Cash compounds into EBITDA growth. Higher EBITDA x exit multiple = larger equity value at exit. PIK wins for growth companies every time.",
        }

    def draw_term_analysis(self, total_bond: float, initial_draw_pct: float,
                           pro_forma_checkpoints: list) -> dict:
        initial_draw = round(total_bond * initial_draw_pct / 100)
        unreleased = total_bond - initial_draw
        remaining_per_checkpoint = round(unreleased / max(len(pro_forma_checkpoints), 1))

        schedule = [{"event": "closing", "month": 0, "draw_usd": initial_draw,
                     "cumulative_drawn_usd": initial_draw, "unreleased_usd": unreleased,
                     "condition": "none — initial funding"}]

        cumulative = initial_draw
        remaining = unreleased
        for i, cp in enumerate(pro_forma_checkpoints):
            draw = min(remaining_per_checkpoint, remaining)
            cumulative += draw
            remaining -= draw
            schedule.append({
                "event": f"checkpoint_{i+1}",
                "month": cp.get("month", (i + 1) * 12),
                "draw_usd": draw,
                "cumulative_drawn_usd": cumulative,
                "unreleased_usd": remaining,
                "condition": f"EBITDA >= {cp.get('ebitda_target_pct', 100)}% of plan",
                "if_miss": "hold capital — evaluate exit or restructure" if i == len(pro_forma_checkpoints) - 1 else "defer to next checkpoint",
            })

        return {
            "total_bond_usd": total_bond,
            "initial_draw_pct": initial_draw_pct,
            "initial_draw_usd": initial_draw,
            "checkpoints": len(pro_forma_checkpoints),
            "schedule": schedule,
            "optionality": "Unreleased capital = optionality. Deploy for bolt-on, hold for exit, or return at premium.",
            "nest_protection": "NEST never overcommits. Pro forma must validate before next tranche releases.",
        }

    def second_swing_analysis(self, company: dict, unreleased_bond_capital: float,
                              hold_year: int) -> dict:
        ebitda = company.get("ebitda_usd", 20_000_000)
        bolt_on_multiple = 4
        bolt_on_ebitda = round(unreleased_bond_capital / bolt_on_multiple)
        combined_ebitda = ebitda + bolt_on_ebitda
        exit_multiple = 7

        option_a = {
            "strategy": "bolt_on_acquisition",
            "capital_deployed_usd": unreleased_bond_capital,
            "acquired_ebitda_usd": bolt_on_ebitda,
            "combined_ebitda_usd": combined_ebitda,
            "exit_ev_usd": round(combined_ebitda * exit_multiple),
            "nest_equity_usd": round(combined_ebitda * exit_multiple * NEST_EQUITY_KICKER_PCT / 100),
            "timeline": f"Deploy in year {hold_year - 2}, exit year {hold_year}",
        }

        option_b = {
            "strategy": "early_exit_return_capital",
            "capital_returned_usd": unreleased_bond_capital,
            "return_premium_pct": 2,
            "bondholder_return_usd": round(unreleased_bond_capital * 1.02),
            "nest_equity_usd": round(ebitda * exit_multiple * NEST_EQUITY_KICKER_PCT / 100),
        }

        option_c = {
            "strategy": "strategic_buyer_leverage",
            "unreleased_as_leverage_usd": unreleased_bond_capital,
            "negotiation_power": "Unreleased capital shows capacity. Strategic buyer pays premium for platform with dry powder.",
            "estimated_premium_pct": 15,
            "exit_ev_with_premium_usd": round(ebitda * exit_multiple * 1.15),
            "nest_equity_usd": round(ebitda * exit_multiple * 1.15 * NEST_EQUITY_KICKER_PCT / 100),
        }

        best = max([option_a, option_b, option_c], key=lambda x: x["nest_equity_usd"])

        return {
            "unreleased_capital_usd": unreleased_bond_capital,
            "hold_year": hold_year,
            "option_a_bolt_on": option_a,
            "option_b_early_exit": option_b,
            "option_c_strategic_leverage": option_c,
            "recommended": best["strategy"],
            "recommended_nest_equity_usd": best["nest_equity_usd"],
        }

    def lc_capacity_analysis(self, b_tranche_usd: float, months_outstanding: int,
                             realized_ebitda: float) -> dict:
        eligible = months_outstanding >= 12
        advance_rate = 0.70 if months_outstanding >= 18 else 0.50 if months_outstanding >= 12 else 0
        lc_capacity = round(b_tranche_usd * advance_rate)

        return {
            "b_tranche_usd": b_tranche_usd,
            "months_outstanding": months_outstanding,
            "eligible_for_lc": eligible,
            "advance_rate_pct": round(advance_rate * 100),
            "lc_capacity_usd": lc_capacity,
            "lc_fee_annual_pct": 1.5,
            "annual_lc_fee_usd": round(lc_capacity * 0.015),
            "uses": ["back_next_acquisition", "reduce_surety_premiums", "fund_bridge_needs"],
            "approval_path": "Treasury product — no credit officer review. Fee-based.",
            "realized_ebitda_usd": realized_ebitda,
            "ebitda_coverage": round(realized_ebitda / lc_capacity, 2) if lc_capacity else 0,
        }

    def balance_sheet_analysis(self, company_pre: dict, bond_structure: dict) -> dict:
        ebitda = company_pre.get("ebitda_usd", 20_000_000)
        total_assets = company_pre.get("total_assets_usd", 100_000_000)
        existing_debt = company_pre.get("existing_debt_usd", 0)
        book_equity = company_pre.get("book_equity_usd", total_assets - existing_debt)

        a_amount = bond_structure.get("a_tranche", {}).get("amount_usd", 0)
        b_amount = bond_structure.get("b_tranche", {}).get("amount_usd", 0)
        total_bond = a_amount + b_amount
        a_rate = bond_structure.get("a_tranche", {}).get("rate_pct", 7.0)
        b_rate = bond_structure.get("b_tranche", {}).get("rate_pct", 12.0)

        lev_loan_amount = total_bond
        lev_rate = 9.0
        lev_annual_pi = round(lev_loan_amount * lev_rate / 100)

        bond_annual_interest = round(a_amount * a_rate / 100)

        lev_loan = {
            "structure": "Senior leveraged loan",
            "total_debt_usd": lev_loan_amount + existing_debt,
            "debt_to_ebitda": round((lev_loan_amount + existing_debt) / ebitda, 2) if ebitda else 0,
            "interest_coverage": round(ebitda / lev_annual_pi, 2) if lev_annual_pi else 0,
            "debt_to_book_cap_pct": round((lev_loan_amount + existing_debt) / (lev_loan_amount + existing_debt + book_equity) * 100, 1),
            "cash_to_debt_service_pct": round(ebitda / lev_annual_pi * 100, 1) if lev_annual_pi else 0,
            "annual_pi_usd": lev_annual_pi,
            "free_cash_after_service_usd": ebitda - lev_annual_pi,
            "problems": [
                "Goes to highest level credit officer",
                "Senior debt kills leverage ratios",
                "Covenants restrict operations",
                "P&I bleeds cash flow",
                "Next credit officer sees trainwreck",
            ],
        }

        nest_bond = {
            "structure": "NEST M&A bond (A + B tranche)",
            "total_debt_usd": a_amount + existing_debt,
            "b_tranche_as_asset_usd": b_amount,
            "effective_net_debt_usd": a_amount + existing_debt - b_amount,
            "debt_to_ebitda": round((a_amount + existing_debt) / ebitda, 2) if ebitda else 0,
            "interest_coverage": round(ebitda / bond_annual_interest, 2) if bond_annual_interest else 0,
            "debt_to_book_cap_pct": round((a_amount + existing_debt) / (a_amount + existing_debt + book_equity + b_amount) * 100, 1),
            "cash_to_debt_service_pct": round(ebitda / bond_annual_interest * 100, 1) if bond_annual_interest else 0,
            "annual_cash_service_usd": bond_annual_interest,
            "free_cash_after_service_usd": ebitda - bond_annual_interest,
            "advantages": [
                "A tranche: investment grade, clean structure",
                "B tranche: balance sheet as marketable security",
                "No P&I during hold: cash accumulates, EBITDA grows",
                "Debt-to-book cap improves as earnings retained",
                "Next credit officer sees well-capitalized company",
                "LC capacity created from B tranche performance",
            ],
        }

        return {
            "company": company_pre.get("name", "Target Co"),
            "ebitda_usd": ebitda,
            "leveraged_loan": lev_loan,
            "nest_bond": nest_bond,
            "cash_flow_advantage_usd": nest_bond["free_cash_after_service_usd"] - lev_loan["free_cash_after_service_usd"],
            "leverage_improvement_x": round(lev_loan["debt_to_ebitda"] - nest_bond["debt_to_ebitda"], 2),
            "verdict": "NEST bond preserves cash flow, improves leverage optics, creates LC capacity. Leveraged loan destroys all three.",
        }


ma_bond_engine = MABondEngine()
