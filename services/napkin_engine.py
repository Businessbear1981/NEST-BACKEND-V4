"""
Back of the Napkin — Quick RMA Spread Calculators.
Two modes: Owner/User (business banking) and Investor RE (property).
Eyes into the company/property in 30 seconds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _grade(value: float, thresholds: list[tuple[float, str]]) -> str:
    """Grade a metric against thresholds. Returns 'strong' / 'adequate' / 'watch' / 'concern'."""
    for threshold, grade in thresholds:
        if value >= threshold:
            return grade
    return thresholds[-1][1] if thresholds else "watch"


def _grade_inverse(value: float, thresholds: list[tuple[float, str]]) -> str:
    """Grade where LOWER is better (leverage, debt ratios)."""
    for threshold, grade in thresholds:
        if value <= threshold:
            return grade
    return thresholds[-1][1] if thresholds else "concern"


def _fmt(value: float, style: str = "ratio") -> str:
    """Format for display. ratio=1.82x, pct=62%, days=38, money=$7.8M"""
    if style == "ratio":
        return f"{value:.2f}x"
    if style == "pct":
        return f"{value:.1f}%"
    if style == "days":
        return f"{int(round(value))}"
    if style == "money":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:.0f}K"
        return f"${value:,.0f}"
    return f"{value:.2f}"


# ═══════════════════════════════════════════════════════════════════
# OWNER / USER — Business Banking
# Eyes into the company. How are they funding the business?
# ═══════════════════════════════════════════════════════════════════

def owner_user_napkin(data: dict[str, Any]) -> dict[str, Any]:
    """
    Back of the Napkin — Owner/User spread.

    Input fields:
      cash, accounts_receivable, inventory, current_assets, current_liabilities,
      total_assets, total_liabilities, total_equity, tangible_net_worth,
      revenue, cogs, ebitda, interest_expense, total_debt, funded_debt,
      officers_comp, officers_debt_pi, tax_rate_pct,
      rent_expense, depreciation, net_income,
      io_payments, pi_payments  (annual debt service components)

    All dollar amounts in actual dollars (not thousands/millions).
    """
    # Extract inputs with defaults
    cash = data.get("cash", 0)
    ar = data.get("accounts_receivable", 0)
    inventory = data.get("inventory", 0)
    current_assets = data.get("current_assets", 0)
    current_liabilities = data.get("current_liabilities", 0)
    total_assets = data.get("total_assets", 0)
    total_liabilities = data.get("total_liabilities", 0)
    total_equity = data.get("total_equity", 0)
    tnw = data.get("tangible_net_worth", total_equity)
    revenue = data.get("revenue", 0)
    cogs = data.get("cogs", 0)
    ebitda = data.get("ebitda", 0)
    interest_expense = data.get("interest_expense", 0)
    total_debt = data.get("total_debt", total_liabilities)
    funded_debt = data.get("funded_debt", total_debt)
    officers_comp = data.get("officers_comp", 0)
    officers_debt_pi = data.get("officers_debt_pi", 0)
    tax_rate = data.get("tax_rate_pct", 21) / 100
    rent_expense = data.get("rent_expense", 0)
    depreciation = data.get("depreciation", 0)
    net_income = data.get("net_income", 0)
    io_payments = data.get("io_payments", 0)
    pi_payments = data.get("pi_payments", 0)

    # ── Ratios ────────────────────────────────────────────────
    quick_ratio = (cash + ar) / max(current_liabilities, 1)
    current_ratio = current_assets / max(current_liabilities, 1)
    ar_days = (ar / max(revenue, 1)) * 365
    ap_days = (data.get("accounts_payable", 0) / max(cogs, 1)) * 365
    leverage = total_liabilities / max(tnw, 1)
    funded_debt_ebitda = funded_debt / max(ebitda, 1)
    ebitda_interest = ebitda / max(interest_expense, 1)
    debt_book_cap = total_debt / max(total_debt + total_equity, 1) * 100

    # ── Cash Flow Analysis (sub-$30M methodology) ─────────────
    adjusted_cf = ebitda * (1 - tax_rate) + rent_expense
    noi_personal = net_income + interest_expense + depreciation
    total_debt_service = io_payments + pi_payments

    # Officer discretionary
    officer_living = officers_comp / 2  # 50% for cost of living, tax, expenses
    officer_discretionary = officer_living - officers_debt_pi
    if officer_discretionary < 0:
        officer_discretionary = 0

    global_cash_flow = adjusted_cf + officer_discretionary
    dscr = global_cash_flow / max(total_debt_service, 1)

    # ── Grade each metric ─────────────────────────────────────
    metrics = [
        {
            "name": "Quick Ratio",
            "value": round(quick_ratio, 2),
            "display": _fmt(quick_ratio),
            "grade": _grade(quick_ratio, [(1.5, "strong"), (1.0, "adequate"), (0.7, "watch")]),
            "read": "Can they pay bills now without selling inventory",
        },
        {
            "name": "Current Ratio",
            "value": round(current_ratio, 2),
            "display": _fmt(current_ratio),
            "grade": _grade(current_ratio, [(2.0, "strong"), (1.2, "adequate"), (0.8, "watch")]),
            "read": "0-12 month expense coverage — not a deal killer alone",
        },
        {
            "name": "AR Days",
            "value": round(ar_days),
            "display": _fmt(ar_days, "days"),
            "grade": _grade_inverse(ar_days, [(30, "strong"), (45, "adequate"), (60, "watch")]),
            "read": "How fast they collect — tells you about their customers",
        },
        {
            "name": "AP Days",
            "value": round(ap_days),
            "display": _fmt(ap_days, "days"),
            "grade": _grade_inverse(ap_days, [(30, "strong"), (45, "adequate"), (60, "watch")]),
            "read": "How fast they pay — tells you about vendor relationships",
        },
        {
            "name": "Leverage",
            "value": round(leverage, 2),
            "display": _fmt(leverage),
            "grade": _grade_inverse(leverage, [(3.0, "strong"), (4.0, "adequate"), (5.0, "watch")]),
            "read": "THE question — funding growth from operations or from debt?",
        },
        {
            "name": "Funded Debt / EBITDA",
            "value": round(funded_debt_ebitda, 2),
            "display": _fmt(funded_debt_ebitda),
            "grade": _grade_inverse(funded_debt_ebitda, [(3.0, "strong"), (4.5, "adequate"), (6.0, "watch")]),
            "read": "Years of earnings to pay off debt",
        },
        {
            "name": "EBITDA / Interest",
            "value": round(ebitda_interest, 2),
            "display": _fmt(ebitda_interest),
            "grade": _grade(ebitda_interest, [(3.5, "strong"), (2.25, "adequate"), (1.5, "watch")]),
            "read": "Interest coverage — can you service what you owe",
        },
        {
            "name": "Debt / Book Cap",
            "value": round(debt_book_cap, 1),
            "display": _fmt(debt_book_cap, "pct"),
            "grade": _grade_inverse(debt_book_cap, [(50, "strong"), (65, "adequate"), (80, "watch")]),
            "read": "Capital structure — how much is debt vs equity",
        },
    ]

    # ── Officer's read ────────────────────────────────────────
    leverage_read = ""
    if leverage <= 3.0:
        leverage_read = "Healthy leverage. Funding growth from operations and retained earnings."
    elif leverage <= 4.0:
        leverage_read = "Moderate leverage. Acceptable but watch the trend — are they growing into it or drowning?"
    elif leverage <= 5.0:
        leverage_read = "Elevated leverage. Could work with SBA enhancement. Need to understand the WHY."
    else:
        leverage_read = "High leverage. Am I funding your growth? Need a clear path to deleveraging."

    concerns = [m["name"] for m in metrics if m["grade"] == "concern"]
    watches = [m["name"] for m in metrics if m["grade"] == "watch"]

    return {
        "type": "owner_user",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "cash_flow_analysis": {
            "ebitda": round(ebitda, 2),
            "adjusted_cf": round(adjusted_cf, 2),
            "officer_discretionary": round(officer_discretionary, 2),
            "global_cash_flow": round(global_cash_flow, 2),
            "total_debt_service": round(total_debt_service, 2),
            "dscr": round(dscr, 2),
            "dscr_display": _fmt(dscr),
            "dscr_grade": _grade(dscr, [(1.5, "strong"), (1.25, "adequate"), (1.0, "watch")]),
        },
        "leverage_read": leverage_read,
        "concerns": concerns,
        "watches": watches,
        "verdict": "proceed" if not concerns and len(watches) <= 2 else "review" if not concerns else "caution",
    }


# ═══════════════════════════════════════════════════════════════════
# INVESTOR REAL ESTATE
# Eyes into the property. Tenants, leases, cap rates, LTV.
# ═══════════════════════════════════════════════════════════════════

def investor_re_napkin(data: dict[str, Any]) -> dict[str, Any]:
    """
    Back of the Napkin — Investor RE spread.

    Input fields:
      noi, cap_rate_pct, purchase_price (optional, overrides implied value),
      requested_loan, coupon_pct, loan_term_years, amortization_years,
      occupancy_pct, total_units_or_sf,
      tenants: [{ name, annual_rent, lease_expiry, lease_type, pct_of_noi }],
      capex_reserve, deferred_maintenance,
      phase_i_clear (bool), replacement_cost
    """
    noi = data.get("noi", 0)
    cap_rate = data.get("cap_rate_pct", 6.5) / 100
    purchase_price = data.get("purchase_price", 0)
    coupon = data.get("coupon_pct", 6.5) / 100
    loan_term = data.get("loan_term_years", 3)
    amort_years = data.get("amortization_years", 30)
    occupancy = data.get("occupancy_pct", 0)
    tenants = data.get("tenants", [])
    capex = data.get("capex_reserve", 0)
    deferred_maint = data.get("deferred_maintenance", 0)
    phase_i_clear = data.get("phase_i_clear", True)
    replacement_cost = data.get("replacement_cost", 0)

    # ── Value & LTV ───────────────────────────────────────────
    implied_value = noi / max(cap_rate, 0.001)
    value = purchase_price if purchase_price > 0 else implied_value
    requested_loan = data.get("requested_loan", value * 0.65)
    ltv = (requested_loan / max(value, 1)) * 100

    # Cap rate inverse — the multiple
    cap_multiple = 1 / max(cap_rate, 0.001)

    # ── Debt Service & DSCR ───────────────────────────────────
    # IO payments (interest only during bond term)
    annual_io = requested_loan * coupon
    # P&I (amortizing)
    monthly_rate = coupon / 12
    n_payments = amort_years * 12
    if monthly_rate > 0 and n_payments > 0:
        monthly_pi = requested_loan * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        annual_pi = monthly_pi * 12
    else:
        annual_pi = annual_io

    dscr_io = noi / max(annual_io, 1)
    dscr_pi = noi / max(annual_pi, 1)
    icr = noi / max(annual_io, 1)  # same as DSCR on IO

    # ── Tenant Analysis ───────────────────────────────────────
    total_tenant_rent = sum(t.get("annual_rent", 0) for t in tenants)
    top_tenant = max(tenants, key=lambda t: t.get("annual_rent", 0)) if tenants else None
    top_tenant_pct = (top_tenant["annual_rent"] / max(noi, 1) * 100) if top_tenant else 0

    # WALT — weighted average lease term
    now = datetime.utcnow()
    walt_num = 0
    walt_den = 0
    for t in tenants:
        rent = t.get("annual_rent", 0)
        expiry = t.get("lease_expiry", "")
        if expiry and rent > 0:
            try:
                exp_date = datetime.strptime(expiry, "%Y-%m-%d")
                years_remaining = max(0, (exp_date - now).days / 365)
                walt_num += rent * years_remaining
                walt_den += rent
            except ValueError:
                pass
    walt = walt_num / max(walt_den, 1)

    # Lease type breakdown
    nnn_count = sum(1 for t in tenants if t.get("lease_type", "").upper() in ("NNN", "TRIPLE NET"))
    gross_count = sum(1 for t in tenants if t.get("lease_type", "").upper() in ("GROSS", "MODIFIED GROSS"))

    # Concentration risk
    concentration_risk = "low"
    if top_tenant_pct > 50:
        concentration_risk = "high"
    elif top_tenant_pct > 30:
        concentration_risk = "moderate"

    # ── Replacement cost check ────────────────────────────────
    loan_to_replacement = (requested_loan / max(replacement_cost, 1) * 100) if replacement_cost > 0 else 0

    # ── Build metrics ─────────────────────────────────────────
    metrics = [
        {
            "name": "NOI",
            "value": round(noi, 2),
            "display": _fmt(noi, "money"),
            "grade": "strong" if noi > 0 else "concern",
            "read": "Net operating income — revenue after operating expenses, before debt",
        },
        {
            "name": "Cap Rate",
            "value": round(cap_rate * 100, 2),
            "display": _fmt(cap_rate * 100, "pct"),
            "grade": _grade_inverse(cap_rate * 100, [(5.0, "strong"), (7.0, "adequate"), (9.0, "watch")]),
            "read": f"Market yield = {cap_multiple:.1f}x multiple. Lower cap = higher value = less risk priced in",
        },
        {
            "name": "Implied Value",
            "value": round(implied_value, 2),
            "display": _fmt(implied_value, "money"),
            "grade": "info",
            "read": "NOI / Cap Rate — what the market says this is worth",
        },
        {
            "name": "LTV",
            "value": round(ltv, 1),
            "display": _fmt(ltv, "pct"),
            "grade": _grade_inverse(ltv, [(55, "strong"), (65, "adequate"), (75, "watch")]),
            "read": "THE constraint. How much debt vs. value.",
        },
        {
            "name": "DSCR (IO)",
            "value": round(dscr_io, 2),
            "display": _fmt(dscr_io),
            "grade": _grade(dscr_io, [(1.5, "strong"), (1.25, "adequate"), (1.0, "watch")]),
            "read": "NOI covers interest-only payments this many times over",
        },
        {
            "name": "DSCR (P&I)",
            "value": round(dscr_pi, 2),
            "display": _fmt(dscr_pi),
            "grade": _grade(dscr_pi, [(1.40, "strong"), (1.20, "adequate"), (1.0, "watch")]),
            "read": "NOI covers full amortizing payments — the real test at stabilization",
        },
        {
            "name": "ICR",
            "value": round(icr, 2),
            "display": _fmt(icr),
            "grade": _grade(icr, [(3.5, "strong"), (2.25, "adequate"), (1.5, "watch")]),
            "read": "Interest coverage ratio — safety margin on debt service",
        },
        {
            "name": "Occupancy",
            "value": round(occupancy, 1),
            "display": _fmt(occupancy, "pct"),
            "grade": _grade(occupancy, [(90, "strong"), (80, "adequate"), (70, "watch")]),
            "read": "NOI means nothing if tenants aren't paying",
        },
    ]

    tenant_analysis = {
        "total_tenants": len(tenants),
        "total_annual_rent": round(total_tenant_rent, 2),
        "walt_years": round(walt, 1),
        "walt_grade": _grade(walt, [(7, "strong"), (4, "adequate"), (2, "watch")]),
        "top_tenant": top_tenant.get("name", "N/A") if top_tenant else "N/A",
        "top_tenant_pct_noi": round(top_tenant_pct, 1),
        "concentration_risk": concentration_risk,
        "nnn_leases": nnn_count,
        "gross_leases": gross_count,
        "lease_mix_read": f"{nnn_count} NNN, {gross_count} gross" + (" — NNN dominant, predictable NOI" if nnn_count > gross_count else " — gross heavy, landlord absorbs cost risk"),
    }

    concerns = [m["name"] for m in metrics if m["grade"] == "concern"]
    watches = [m["name"] for m in metrics if m["grade"] == "watch"]

    # Build the officer's read
    reads = []
    if dscr_io >= 1.25 and ltv <= 70:
        reads.append("Solid NOI, debt service covers comfortably.")
    if walt >= 5:
        reads.append(f"WALT {walt:.1f}yrs supports the term.")
    if concentration_risk == "high":
        reads.append(f"Watch: {top_tenant_pct:.0f}% NOI concentration in {top_tenant.get('name', 'top tenant')}. Renewal risk.")
    elif concentration_risk == "moderate":
        reads.append(f"Moderate concentration: {top_tenant_pct:.0f}% in {top_tenant.get('name', 'top tenant')}.")
    if occupancy < 80:
        reads.append(f"Occupancy {occupancy:.0f}% — lease-up risk. Need stabilization runway.")
    if not phase_i_clear:
        reads.append("Phase I not clear — environmental risk. Standard lending stops here. Bond structure may work (Phoenix).")
    if deferred_maint > noi * 0.5:
        reads.append("Deferred maintenance exceeds 50% of NOI — capital calls ahead.")
    if loan_to_replacement > 80:
        reads.append(f"Loan-to-replacement {loan_to_replacement:.0f}% — cushion is thinner than LTV suggests.")

    return {
        "type": "investor_re",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "debt_service": {
            "requested_loan": round(requested_loan, 2),
            "annual_io": round(annual_io, 2),
            "annual_pi": round(annual_pi, 2),
            "coupon_pct": round(coupon * 100, 2),
        },
        "tenant_analysis": tenant_analysis,
        "cap_rate_explainer": {
            "cap_rate_pct": round(cap_rate * 100, 2),
            "multiple": round(cap_multiple, 1),
            "inverse_relationship": "Cap rate DOWN = value UP (market says safe). Cap rate UP = value DOWN (market says risky).",
        },
        "environmental": {
            "phase_i_clear": phase_i_clear,
            "read": "Clear" if phase_i_clear else "NOT CLEAR — environmental risk present",
        },
        "replacement_cost": {
            "replacement_cost": round(replacement_cost, 2),
            "loan_to_replacement_pct": round(loan_to_replacement, 1),
        } if replacement_cost > 0 else None,
        "officers_read": reads,
        "concerns": concerns,
        "watches": watches,
        "verdict": "proceed" if not concerns and len(watches) <= 2 else "review" if not concerns else "caution",
    }
