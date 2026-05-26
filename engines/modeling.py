"""
NEST Modeling Module — Silo 3
Multi-view financial engine: same underlying data, different views per gatekeeper.

Views:
  NOI, EBITDA, DSCR, Leverage, CCSR, P-A-T-A,
  Entrance Fee Velocity, Principal Sweep,
  Construction Amortization, Global Cash Flow, Statement of Cash Flows
"""
from typing import List, Dict, Optional
from datetime import datetime


def compute_noi(revenue: float, opex: float) -> dict:
    """Net Operating Income = Revenue - Operating Expenses."""
    noi = revenue - opex
    return {
        "revenue": round(revenue, 2),
        "opex": round(opex, 2),
        "noi": round(noi, 2),
        "noi_margin_pct": round(noi / revenue * 100, 2) if revenue > 0 else 0,
    }


def compute_ebitda(noi: float, management_fee: float = 0,
                   reserve_contribution: float = 0) -> dict:
    """EBITDA from NOI less management fee and reserves."""
    ebitda = noi - management_fee - reserve_contribution
    return {
        "noi": round(noi, 2),
        "management_fee": round(management_fee, 2),
        "reserve_contribution": round(reserve_contribution, 2),
        "ebitda": round(ebitda, 2),
    }


def compute_dscr(noi: float, annual_debt_service: float,
                 scenario: str = "base") -> dict:
    """
    Debt Service Coverage Ratio.
    DSCR = NOI / Annual Debt Service.
    """
    dscr = round(noi / annual_debt_service, 3) if annual_debt_service > 0 else 0
    status = ("green" if dscr >= 1.5 else "yellow" if dscr >= 1.2
              else "red" if dscr >= 1.0 else "critical")
    return {
        "noi": round(noi, 2),
        "annual_debt_service": round(annual_debt_service, 2),
        "dscr": dscr,
        "scenario": scenario,
        "status": status,
        "investment_grade": dscr >= 1.5,
    }


def compute_leverage(total_debt: float, noi: float, equity: float,
                     ebitda: float, appraised_value: float) -> dict:
    """
    Multi-lens leverage view:
    - Cash flow leverage = Debt / NOI
    - Balance sheet leverage = Debt / Equity
    - Debt-to-EBITDA = Debt / EBITDA
    - LTV = Debt / Appraised Value
    - Debt/Cap = Debt / (Debt + Equity)
    """
    cf_lev = round(total_debt / noi, 3) if noi > 0 else 0
    bs_lev = round(total_debt / equity, 3) if equity > 0 else 0
    de = round(total_debt / ebitda, 3) if ebitda > 0 else 0
    ltv = round(total_debt / appraised_value * 100, 2) if appraised_value > 0 else 0
    debt_cap = round(total_debt / (total_debt + equity) * 100, 2) if (total_debt + equity) > 0 else 0

    return {
        "total_debt": round(total_debt),
        "cash_flow_leverage": cf_lev,
        "balance_sheet_leverage": bs_lev,
        "debt_to_ebitda": de,
        "ltv_pct": ltv,
        "debt_to_cap_pct": debt_cap,
        "ltv_alert": ltv > 75.0,
    }


def compute_ccsr(cash_on_hand: float, debt_service_next_12mo: float,
                 operating_reserves: float = 0,
                 restricted_cash: float = 0) -> dict:
    """
    Cash Coverage Service Ratio — cash-at-hand view vs GAAP smoothed.
    The framing Sean used in the Jacaranda lender email.
    CCSR = (Cash on Hand + Operating Reserves - Restricted) / DS_12mo
    """
    available = cash_on_hand + operating_reserves - restricted_cash
    ccsr = round(available / debt_service_next_12mo, 3) if debt_service_next_12mo > 0 else 0
    return {
        "cash_on_hand": round(cash_on_hand),
        "operating_reserves": round(operating_reserves),
        "restricted_cash": round(restricted_cash),
        "available_cash": round(available),
        "debt_service_next_12mo": round(debt_service_next_12mo),
        "ccsr": ccsr,
        "status": "green" if ccsr >= 1.5 else "yellow" if ccsr >= 1.0 else "red",
        "note": "Cash basis — counters GAAP amortization smoothing",
    }


def compute_pata(gross_revenue: float, operating_expenses: float,
                 tax_rate: float, amortization: float,
                 interest_expense: float = 0) -> dict:
    """
    Profit After Tax After Amortization — bridge loan economics.
    The Jacaranda framing for credit committee.
    P-A-T-A = (Revenue - OpEx - Interest) * (1 - tax_rate) - Amortization
    """
    ebt = gross_revenue - operating_expenses - interest_expense
    tax = ebt * tax_rate if ebt > 0 else 0
    eat = ebt - tax
    pata = eat - amortization
    return {
        "gross_revenue": round(gross_revenue),
        "operating_expenses": round(operating_expenses),
        "interest_expense": round(interest_expense),
        "earnings_before_tax": round(ebt),
        "tax": round(tax),
        "earnings_after_tax": round(eat),
        "amortization": round(amortization),
        "pata": round(pata),
        "pata_margin_pct": round(pata / gross_revenue * 100, 2) if gross_revenue > 0 else 0,
    }


def compute_entrance_fee_velocity(total_units: int, turnover_units: int,
                                  gross_fees: float, refunds: float,
                                  period_label: str = "annual") -> dict:
    """
    Entrance fee velocity — CCRC/Life Plan structures (Jacaranda).
    Validation gate: must reproduce 2023 audited (27 units, $11.59M gross,
    $3.31M refund, $8.28M net, 13.4% turnover on 201 stabilized).
    """
    net_fees = gross_fees - refunds
    turnover_pct = round(turnover_units / total_units * 100, 1) if total_units > 0 else 0
    avg_gross = round(gross_fees / turnover_units) if turnover_units > 0 else 0
    avg_refund = round(refunds / turnover_units) if turnover_units > 0 else 0

    return {
        "period": period_label,
        "total_units": total_units,
        "turnover_units": turnover_units,
        "turnover_pct": turnover_pct,
        "gross_entrance_fees": round(gross_fees),
        "refunds": round(refunds),
        "net_entrance_fees": round(net_fees),
        "avg_gross_per_unit": avg_gross,
        "avg_refund_per_unit": avg_refund,
        "avg_net_per_unit": avg_gross - avg_refund,
    }


def compute_principal_sweep(beginning_balance: float, net_cash_flow: float,
                            sweep_pct: float = 1.0,
                            minimum_balance: float = 0) -> dict:
    """
    Principal sweep — configurable % of excess cash applied to principal.
    Jacaranda uses 100% and 85% scenarios.
    """
    available = max(0, net_cash_flow)
    sweep_amount = available * sweep_pct
    ending_balance = max(minimum_balance, beginning_balance - sweep_amount)
    actual_sweep = beginning_balance - ending_balance

    return {
        "beginning_balance": round(beginning_balance),
        "net_cash_flow": round(net_cash_flow),
        "sweep_pct": sweep_pct,
        "sweep_amount": round(actual_sweep),
        "ending_balance": round(ending_balance),
        "paydown_pct": round(actual_sweep / beginning_balance * 100, 2) if beginning_balance > 0 else 0,
    }


def compute_construction_amortization(total_budget: float,
                                      draws: List[dict],
                                      contingency_pct: float = 0.05) -> dict:
    """
    Construction loan amortization — Petersburg-style.
    draws: [{"month": 1, "amount": X, "milestone": "foundation"}, ...]
    """
    total_drawn = sum(d["amount"] for d in draws)
    remaining = total_budget - total_drawn
    contingency = total_budget * contingency_pct
    completion_pct = round(total_drawn / total_budget * 100, 1) if total_budget > 0 else 0

    cost_overrun = total_drawn > (total_budget - contingency)

    return {
        "total_budget": round(total_budget),
        "total_drawn": round(total_drawn),
        "remaining": round(remaining),
        "contingency": round(contingency),
        "completion_pct": completion_pct,
        "draws": draws,
        "cost_overrun_alert": cost_overrun,
        "months_of_draws": len(draws),
    }


def run_stress_scenario(base_noi: float, base_debt_service: float,
                        total_debt: float, scenario: str = "base") -> dict:
    """
    Run stress scenarios against base case.
    Matches the 4 scenarios from services/core.py CreditEngine.stress().
    """
    configs = {
        "base":         (0,   0,  0,  "All assumptions as modeled"),
        "downside":     (-15, 10, 0,  "-15% revenue, +10% costs"),
        "stress":       (-25, 20, 6,  "-25% revenue, +20% costs, +6mo delay"),
        "catastrophic": (-40, 30, 0,  "-40% revenue — COVID/hurricane scenario"),
    }

    results = {}
    for name, (rev_shock, cost_shock, delay_months, desc) in configs.items():
        adj_noi = base_noi * (1 + rev_shock / 100) - total_debt * 0.07 * delay_months / 12
        adj_ds = base_debt_service * (1 + cost_shock / 200)
        dscr = round(adj_noi / adj_ds, 3) if adj_ds > 0 else 0

        results[name] = {
            "description": desc,
            "shocked_noi": round(max(0, adj_noi)),
            "adjusted_debt_service": round(adj_ds),
            "dscr": dscr,
            "status": ("green" if dscr >= 1.5 else "yellow" if dscr >= 1.2
                       else "red" if dscr >= 1.0 else "critical"),
            "surety_triggered": dscr < 1.0,
        }

    return results
