"""
Rating Agency Benchmarks — Confirmed financial ratio thresholds from
Moody's and S&P published methodologies.

These drive:
1. What data to collect from clients (via Roots doc ingestion)
2. What the credit memo analyzes
3. What the rating agent scores against
4. What the structuring engine optimizes toward

Sources: Moody's corporate methodology (ratings.moodys.com),
S&P corporate methodology (spglobal.com/ratings), public presentations,
academic analysis of published criteria.
"""

# ══════════════════════════════════════════════════════════════
# S&P FINANCIAL RISK PROFILE — CONFIRMED BENCHMARKS
# Source: S&P Global Corporate Methodology (January 2024)
# ══════════════════════════════════════════════════════════════

SP_FINANCIAL_RISK_BENCHMARKS = {
    # Primary ratios — these define the financial risk category
    "ffo_to_debt": {
        "minimal":          {"min": 0.60, "max": None},    # >60%
        "modest":           {"min": 0.45, "max": 0.60},    # 45-60%
        "intermediate":     {"min": 0.30, "max": 0.45},    # 30-45%
        "significant":      {"min": 0.20, "max": 0.30},    # 20-30%
        "aggressive":       {"min": 0.12, "max": 0.20},    # 12-20%
        "highly_leveraged": {"min": None, "max": 0.12},    # <12%
    },
    "debt_to_ebitda": {
        "minimal":          {"min": None, "max": 1.5},     # <1.5x
        "modest":           {"min": 1.5,  "max": 2.0},     # 1.5-2.0x
        "intermediate":     {"min": 2.0,  "max": 3.0},     # 2.0-3.0x
        "significant":      {"min": 3.0,  "max": 4.0},     # 3.0-4.0x
        "aggressive":       {"min": 4.0,  "max": 5.0},     # 4.0-5.0x
        "highly_leveraged": {"min": 5.0,  "max": None},    # >5.0x
    },
    # Supplementary ratios — used for confirmation and sector adjustment
    "ffo_plus_interest_to_cash_interest": {
        "minimal":          {"min": 13.0, "max": None},
        "modest":           {"min": 8.0,  "max": 13.0},
        "intermediate":     {"min": 5.0,  "max": 8.0},
        "significant":      {"min": 3.0,  "max": 5.0},
        "aggressive":       {"min": 2.0,  "max": 3.0},
        "highly_leveraged": {"min": None, "max": 2.0},
    },
    "ebitda_to_interest": {
        "minimal":          {"min": 15.0, "max": None},
        "modest":           {"min": 8.0,  "max": 15.0},
        "intermediate":     {"min": 4.0,  "max": 8.0},
        "significant":      {"min": 2.5,  "max": 4.0},
        "aggressive":       {"min": 1.5,  "max": 2.5},
        "highly_leveraged": {"min": None, "max": 1.5},
    },
    "cfo_to_debt": {
        "minimal":          {"min": 0.50, "max": None},
        "modest":           {"min": 0.35, "max": 0.50},
        "intermediate":     {"min": 0.25, "max": 0.35},
        "significant":      {"min": 0.15, "max": 0.25},
        "aggressive":       {"min": 0.10, "max": 0.15},
        "highly_leveraged": {"min": None, "max": 0.10},
    },
    "focf_to_debt": {
        "minimal":          {"min": 0.40, "max": None},
        "modest":           {"min": 0.25, "max": 0.40},
        "intermediate":     {"min": 0.15, "max": 0.25},
        "significant":      {"min": 0.10, "max": 0.15},
        "aggressive":       {"min": 0.05, "max": 0.10},
        "highly_leveraged": {"min": None, "max": 0.05},
    },
    "dcf_to_debt": {
        "minimal":          {"min": 0.25, "max": None},
        "modest":           {"min": 0.15, "max": 0.25},
        "intermediate":     {"min": 0.10, "max": 0.15},
        "significant":      {"min": 0.05, "max": 0.10},
        "aggressive":       {"min": 0.02, "max": 0.05},
        "highly_leveraged": {"min": None, "max": 0.02},
    },
}

# S&P Business Risk Profile categories
SP_BUSINESS_RISK_CATEGORIES = {
    1: "Excellent",
    2: "Strong",
    3: "Satisfactory",
    4: "Fair",
    5: "Weak",
    6: "Vulnerable",
}

# S&P Financial Risk Profile categories (mapped to scores)
SP_FINANCIAL_RISK_CATEGORIES = {
    1: "Minimal",
    2: "Modest",
    3: "Intermediate",
    4: "Significant",
    5: "Aggressive",
    6: "Highly Leveraged",
}

# S&P Anchor Matrix — Business Risk (row) × Financial Risk (col)
SP_ANCHOR_MATRIX = {
    (1, 1): "AAA", (1, 2): "AA",  (1, 3): "A+",  (1, 4): "A",   (1, 5): "BBB",  (1, 6): "BB+",
    (2, 1): "AA",  (2, 2): "A+",  (2, 3): "A",   (2, 4): "A-",  (2, 5): "BBB-", (2, 6): "BB",
    (3, 1): "A+",  (3, 2): "A",   (3, 3): "BBB+", (3, 4): "BBB", (3, 5): "BB+",  (3, 6): "BB-",
    (4, 1): "A",   (4, 2): "BBB+", (4, 3): "BBB", (4, 4): "BBB-", (4, 5): "BB",  (4, 6): "B+",
    (5, 1): "BBB", (5, 2): "BBB-", (5, 3): "BB+", (5, 4): "BB",  (5, 5): "BB-",  (5, 6): "B",
    (6, 1): "BB+", (6, 2): "BB",  (6, 3): "BB-", (6, 4): "B+",  (6, 5): "B",    (6, 6): "B-",
}

# S&P Modifier adjustments (notches from anchor)
SP_MODIFIERS = {
    "diversification":    {"positive": -1, "neutral": 0, "negative": +1},
    "capital_structure":  {"positive": -1, "neutral": 0, "negative": +1},
    "financial_policy":   {"positive": -1, "neutral": 0, "negative": +1, "very_negative": +2},
    "liquidity":          {"strong": -1, "adequate": 0, "less_than_adequate": +1, "weak": +2},
    "management_governance": {"strong": -1, "satisfactory": 0, "fair": +1, "weak": +2},
}

# S&P Enhancement / Structural notching
SP_ENHANCEMENT_OVERRIDES = {
    "bond_insurance":         "Lifts to insurer rating (typically AA)",
    "loc_investment_grade":   "Lifts to LC bank short-term rating",
    "cash_collateralized_lc": "AAA equivalent",
    "federal_guarantee":      "AAA (FHA/USDA/GNMA backed)",
    "surety":                 "+1 to +3 notches depending on provider rating",
}

SP_SUBORDINATION_NOTCHING = {
    "senior_secured":   0,       # No notch — highest priority
    "senior_unsecured": 0,       # Typically at anchor for IG; -1 for HY
    "subordinated":     -1,      # One notch below senior
    "junior_subordinated": -2,   # Two notches below senior
}

SP_RECOVERY_RATINGS = {
    "1+": {"recovery": "95-100%", "notch": +3},
    "1":  {"recovery": "90-100%", "notch": +2},
    "2":  {"recovery": "70-90%",  "notch": +1},
    "3":  {"recovery": "50-70%",  "notch": 0},
    "4":  {"recovery": "30-50%",  "notch": -1},
    "5":  {"recovery": "10-30%",  "notch": -2},
    "6":  {"recovery": "0-10%",   "notch": -3},
}


# ══════════════════════════════════════════════════════════════
# MOODY'S CORPORATE SCORECARD — CONFIRMED BENCHMARKS
# Source: Moody's Corporate Methodology (Nov 2023)
# Note: Moody's uses sector-specific scorecards. These are the
# GENERAL corporate ranges. Each sector adjusts the endpoints.
# ══════════════════════════════════════════════════════════════

MOODYS_FINANCIAL_METRICS = {
    "debt_to_ebitda": {
        "Aaa": {"max": 1.5},
        "Aa":  {"min": 1.5, "max": 2.5},
        "A":   {"min": 2.5, "max": 3.5},
        "Baa": {"min": 3.5, "max": 4.5},
        "Ba":  {"min": 4.5, "max": 6.0},
        "B":   {"min": 6.0, "max": 8.0},
        "Caa": {"min": 8.0, "max": 12.0},
        "Ca":  {"min": 12.0},
    },
    "rcf_to_net_debt": {
        "Aaa": {"min": 0.55},
        "Aa":  {"min": 0.40, "max": 0.55},
        "A":   {"min": 0.25, "max": 0.40},
        "Baa": {"min": 0.15, "max": 0.25},
        "Ba":  {"min": 0.08, "max": 0.15},
        "B":   {"min": 0.04, "max": 0.08},
        "Caa": {"min": 0.02, "max": 0.04},
        "Ca":  {"max": 0.02},
    },
    "ebitda_minus_capex_to_interest": {
        "Aaa": {"min": 15.0},
        "Aa":  {"min": 10.0, "max": 15.0},
        "A":   {"min": 6.0,  "max": 10.0},
        "Baa": {"min": 3.5,  "max": 6.0},
        "Ba":  {"min": 2.0,  "max": 3.5},
        "B":   {"min": 1.0,  "max": 2.0},
        "Caa": {"min": 0.5,  "max": 1.0},
        "Ca":  {"max": 0.5},
    },
}

# Moody's factor weights (corporate general)
MOODYS_FACTOR_WEIGHTS = {
    "business_profile": 0.35,   # Scale, competitive position, business model
    "financial_policy":  0.10,  # Management's financial risk tolerance
    "leverage_coverage": 0.55,  # Debt/EBITDA, RCF/Net Debt, (EBITDA-Capex)/Interest
}

# Moody's Covenant Quality scores
MOODYS_COVENANT_QUALITY = {
    "CQ1": {"description": "Most protective", "notch_impact": -0.5},
    "CQ2": {"description": "Above average protection", "notch_impact": -0.25},
    "CQ3": {"description": "Average protection", "notch_impact": 0},
    "CQ4": {"description": "Below average protection", "notch_impact": +0.25},
    "CQ5": {"description": "Weakest protection", "notch_impact": +0.5},
}


# ══════════════════════════════════════════════════════════════
# BOND STRUCTURING CRITERIA — From rating agency guidelines
# What structural features produce what rating outcomes
# ══════════════════════════════════════════════════════════════

STRUCTURING_CRITERIA = {
    "dscr_by_rating": {
        "AAA": {"min": 2.50, "typical": 3.00},
        "AA":  {"min": 2.00, "typical": 2.50},
        "A":   {"min": 1.50, "typical": 1.75},
        "BBB": {"min": 1.20, "typical": 1.40},
        "BB":  {"min": 1.10, "typical": 1.20},
        "B":   {"min": 1.00, "typical": 1.10},
    },
    "dsrf_sizing": {
        "standard": "Maximum Annual Debt Service (MADS)",
        "alternative_1": "125% of average annual debt service",
        "alternative_2": "10% of bond proceeds",
        "irc_148d_safe_harbor": "Lesser of MADS, 125% avg ADS, or 10% proceeds",
        "rating_impact": "Funded DSRF at MADS is neutral; below MADS is negative",
    },
    "equity_contribution_by_rating": {
        "AAA": {"min_pct": 0.40},
        "AA":  {"min_pct": 0.35},
        "A":   {"min_pct": 0.30},
        "BBB": {"min_pct": 0.25},
        "BB":  {"min_pct": 0.20},
        "B":   {"min_pct": 0.15},
    },
    "call_protection_norms": {
        "investment_grade_muni": {"nc_years": 10, "call_price": 100},
        "high_yield_corporate": {"nc_years": 3, "step_down": True, "initial_premium": 104},
        "project_finance": {"nc_years": 5, "make_whole": True},
    },
    "covenant_thresholds": {
        "investment_grade": {
            "dscr": 1.20,
            "additional_bonds_test": "1.20x historical",
            "distribution_restriction": "At DSCR below 1.10x",
        },
        "high_yield": {
            "dscr": 1.10,
            "additional_bonds_test": "1.10x historical and projected",
            "restricted_payments": "Builder basket + capacity based on cumulative CNI",
            "change_of_control": "Put at 101",
            "asset_sale_covenant": "Reinvest within 365 days or offer to repurchase",
        },
    },
}


# ══════════════════════════════════════════════════════════════
# REQUIRED CLIENT DATA — What financials to collect/extract
# Maps to what both agencies need to score the deal
# ══════════════════════════════════════════════════════════════

REQUIRED_FINANCIAL_DATA = {
    "income_statement": [
        "revenue",
        "revenue_growth_pct",
        "cost_of_goods_sold",
        "gross_profit",
        "gross_margin_pct",
        "operating_expenses",
        "ebitda",
        "ebitda_margin_pct",
        "depreciation_amortization",
        "ebit",
        "interest_expense",
        "net_income",
    ],
    "balance_sheet": [
        "total_assets",
        "cash_and_equivalents",
        "total_debt",
        "net_debt",
        "total_equity",
        "total_capitalization",
        "working_capital",
        "current_ratio",
    ],
    "cash_flow": [
        "funds_from_operations",  # FFO = net income + D&A + deferred taxes + other non-cash
        "cash_from_operations",   # CFO = FFO +/- working capital changes
        "capital_expenditures",
        "free_operating_cash_flow",  # FOCF = CFO - capex
        "dividends_paid",
        "retained_cash_flow",  # RCF = FFO - dividends
        "discretionary_cash_flow",  # DCF = FOCF - dividends
    ],
    "coverage_ratios": [
        "dscr",                    # NOI or EBITDA / annual debt service
        "ebitda_to_interest",      # EBITDA / interest expense
        "ebitda_minus_capex_to_interest",  # (EBITDA - capex) / interest
        "ffo_to_debt",             # FFO / total debt
        "ffo_plus_interest_to_cash_interest",
        "cfo_to_debt",
        "focf_to_debt",
        "dcf_to_debt",
        "rcf_to_net_debt",
    ],
    "leverage_ratios": [
        "debt_to_ebitda",
        "net_debt_to_ebitda",
        "debt_to_total_capitalization",
        "ltv_pct",                 # for real estate: debt / property value
    ],
    "project_specific": {
        "real_estate": ["noi", "cap_rate", "occupancy_pct", "lease_term_wavg", "tenant_concentration"],
        "construction": ["total_project_cost", "ltc_ratio", "completion_pct", "contingency_pct", "gmp_coverage"],
        "ma_acquisition": ["ev_ebitda_multiple", "sponsor_equity_pct", "rollover_equity", "pro_forma_leverage", "synergies"],
        "working_capital": ["revenue_trend", "ar_days", "ap_days", "inventory_turns", "wc_cycle_days"],
        "equipment": ["equipment_value", "useful_life_years", "depreciation_method", "collateral_coverage"],
    },
}


# ══════════════════════════════════════════════════════════════
# SCORING FUNCTIONS
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# SECTOR-SPECIFIC ADJUSTMENTS
# Standard corporate metrics don't apply to all bond types.
# Each sector has its own primary metrics and thresholds.
# ══════════════════════════════════════════════════════════════

SECTOR_SCORING_OVERRIDES = {
    # CCRCs / Entrance-Fee Communities
    # Standard Debt/EBITDA is WRONG — entrance fees are the primary cash engine.
    # Correct metric: Funds Available for Debt Service (FADS) which includes
    # net entrance fee cash (gross receipts - refunds), not GAAP amortized revenue.
    # Turnover at 10-15% annually generates $18-25M on a 447-unit campus.
    "senior_living": {
        "primary_metric": "dscr",  # DSCR using FADS, not EBITDA
        "secondary_metric": "days_cash_on_hand",
        "adjustments": {
            "entrance_fee_community": {
                "description": "Entrance-fee CCRC — use FADS not EBITDA for coverage",
                "dscr_thresholds": {
                    "Aaa": 3.0, "Aa": 2.5, "A": 2.0, "Baa": 1.50, "Ba": 1.20, "B": 1.05,
                },
                "days_cash_thresholds": {
                    "Aaa": 600, "Aa": 400, "A": 250, "Baa": 150, "Ba": 100, "B": 60,
                },
                "debt_yield_thresholds": {
                    "Aaa": 0.25, "Aa": 0.20, "A": 0.15, "Baa": 0.11, "Ba": 0.08, "B": 0.05,
                },
                "turnover_velocity_factor": True,  # Higher turnover = stronger credit
                "principal_sweep_credit": True,     # Mandatory sweep reduces outstanding
            },
        },
    },
    # Hospitals — days cash on hand is primary, not leverage
    "hospitals": {
        "primary_metric": "dscr",
        "secondary_metric": "days_cash_on_hand",
        "adjustments": {
            "dscr_thresholds": {
                "Aaa": 5.0, "Aa": 3.5, "A": 2.5, "Baa": 1.80, "Ba": 1.40, "B": 1.10,
            },
            "days_cash_thresholds": {
                "Aaa": 400, "Aa": 300, "A": 200, "Baa": 150, "Ba": 90, "B": 50,
            },
            "operating_margin_factor": True,
        },
    },
    # Charter Schools — enrollment is a key driver
    "charter_schools": {
        "primary_metric": "dscr",
        "secondary_metric": "enrollment_stability",
        "adjustments": {
            "dscr_thresholds": {
                "Aaa": 3.0, "Aa": 2.5, "A": 2.0, "Baa": 1.40, "Ba": 1.10, "B": 1.00,
            },
            "enrollment_weight": 0.15,  # Enrollment trend affects 15% of score
        },
    },
    # Multifamily — NOI-based, cap rate driven
    "affordable_multifamily": {
        "primary_metric": "dscr",
        "secondary_metric": "occupancy",
        "adjustments": {
            "dscr_thresholds": {
                "Aaa": 2.5, "Aa": 2.0, "A": 1.60, "Baa": 1.30, "Ba": 1.15, "B": 1.05,
            },
            "ltv_thresholds": {
                "Aaa": 0.50, "Aa": 0.60, "A": 0.70, "Baa": 0.75, "Ba": 0.80, "B": 0.85,
            },
        },
    },
    # Real Estate — NOI/cap rate based
    "real_estate": {
        "primary_metric": "dscr",
        "secondary_metric": "ltv",
        "adjustments": {
            "dscr_thresholds": {
                "Aaa": 2.5, "Aa": 2.0, "A": 1.60, "Baa": 1.30, "Ba": 1.15, "B": 1.05,
            },
            "ltv_thresholds": {
                "Aaa": 0.50, "Aa": 0.60, "A": 0.65, "Baa": 0.70, "Ba": 0.75, "B": 0.80,
            },
        },
    },
}


def score_sp_financial_risk(financials: dict) -> dict:
    """Score a deal's financial risk profile per S&P methodology.

    Applies sector-specific adjustments when sector is provided.
    For CCRCs/entrance-fee communities, uses FADS-based DSCR and
    days cash on hand instead of standard Debt/EBITDA.
    """
    sector = financials.get("sector", "")
    sector_override = SECTOR_SCORING_OVERRIDES.get(sector)

    # If sector has specific scoring (CCRC, hospital, charter school, etc.)
    if sector_override and financials.get("dscr"):
        return _score_sector_specific(financials, sector_override, sector)

    # Standard corporate scoring
    ffo_debt = financials.get("ffo_to_debt", 0)
    debt_ebitda = financials.get("debt_to_ebitda", 99)

    categories = ["minimal", "modest", "intermediate", "significant", "aggressive", "highly_leveraged"]

    # Score FFO/Debt
    ffo_cat = "highly_leveraged"
    for cat in categories:
        bounds = SP_FINANCIAL_RISK_BENCHMARKS["ffo_to_debt"][cat]
        if bounds["min"] is not None and ffo_debt >= bounds["min"]:
            ffo_cat = cat
            break
        elif bounds["min"] is None and bounds["max"] is not None and ffo_debt < bounds["max"]:
            ffo_cat = cat

    # Score Debt/EBITDA
    de_cat = "highly_leveraged"
    for cat in categories:
        bounds = SP_FINANCIAL_RISK_BENCHMARKS["debt_to_ebitda"][cat]
        if bounds["max"] is not None and debt_ebitda <= bounds["max"]:
            de_cat = cat
            break
        elif bounds["max"] is None and bounds["min"] is not None and debt_ebitda > bounds["min"]:
            de_cat = cat

    # Combined (conservative — take the worse of the two)
    cat_scores = {c: i + 1 for i, c in enumerate(categories)}
    combined_score = max(cat_scores.get(ffo_cat, 6), cat_scores.get(de_cat, 6))
    combined_cat = categories[combined_score - 1]

    return {
        "ffo_to_debt": {"value": ffo_debt, "category": ffo_cat, "score": cat_scores[ffo_cat]},
        "debt_to_ebitda": {"value": debt_ebitda, "category": de_cat, "score": cat_scores[de_cat]},
        "combined_category": combined_cat,
        "combined_score": combined_score,
        "sector_adjusted": False,
    }


def _score_sector_specific(financials: dict, override: dict, sector: str) -> dict:
    """Score using sector-specific metrics instead of standard corporate ratios.

    For CCRCs: DSCR (using FADS) + Days Cash + Debt Yield
    For Hospitals: DSCR + Days Cash + Operating Margin
    For Charter Schools: DSCR + Enrollment Stability
    For Multifamily/RE: DSCR + LTV
    """
    dscr = financials.get("dscr", 0)
    days_cash = financials.get("days_cash_on_hand", 0)
    debt_yield = financials.get("debt_yield", 0)
    ltv = financials.get("ltv", financials.get("ltv_pct", 0))

    # Get sector-specific DSCR thresholds
    adj = override.get("adjustments", {})
    # Handle nested structure for senior_living
    if "entrance_fee_community" in adj:
        adj = adj["entrance_fee_community"]

    dscr_thresholds = adj.get("dscr_thresholds", {})
    dcoh_thresholds = adj.get("days_cash_thresholds", {})
    dy_thresholds = adj.get("debt_yield_thresholds", {})
    ltv_thresholds = adj.get("ltv_thresholds", {})

    # Score DSCR against sector thresholds
    dscr_rating = "B"
    for rating in ["Aaa", "Aa", "A", "Baa", "Ba", "B"]:
        if dscr >= dscr_thresholds.get(rating, 99):
            dscr_rating = rating
            break

    # Score Days Cash
    dcoh_rating = "B"
    if dcoh_thresholds:
        for rating in ["Aaa", "Aa", "A", "Baa", "Ba", "B"]:
            if days_cash >= dcoh_thresholds.get(rating, 9999):
                dcoh_rating = rating
                break

    # Score Debt Yield
    dy_rating = None
    if dy_thresholds and debt_yield > 0:
        dy_rating = "B"
        for rating in ["Aaa", "Aa", "A", "Baa", "Ba", "B"]:
            if debt_yield >= dy_thresholds.get(rating, 99):
                dy_rating = rating
                break

    # Score LTV (lower is better)
    ltv_rating = None
    if ltv_thresholds and ltv > 0:
        ltv_rating = "B"
        for rating in ["Aaa", "Aa", "A", "Baa", "Ba", "B"]:
            if ltv <= ltv_thresholds.get(rating, 0):
                ltv_rating = rating
                break

    # Combine — weighted average of available metrics
    rating_scores = {"Aaa": 1, "Aa": 2, "A": 3, "Baa": 4, "Ba": 5, "B": 6}
    scores = [rating_scores.get(dscr_rating, 6)]
    weights = [0.50]  # DSCR always 50%

    if dcoh_thresholds and days_cash > 0:
        scores.append(rating_scores.get(dcoh_rating, 6))
        weights.append(0.25)

    if dy_rating:
        scores.append(rating_scores.get(dy_rating, 6))
        weights.append(0.25)

    if ltv_rating:
        scores.append(rating_scores.get(ltv_rating, 6))
        weights.append(0.25)

    # Normalize weights
    total_weight = sum(weights)
    weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
    combined_score = round(weighted_score)
    combined_score = max(1, min(combined_score, 6))

    # Map back to S&P category
    score_to_cat = {1: "minimal", 2: "modest", 3: "intermediate", 4: "significant", 5: "aggressive", 6: "highly_leveraged"}
    combined_cat = score_to_cat[combined_score]

    # Turnover velocity adjustment for CCRCs
    turnover_adj = ""
    if adj.get("turnover_velocity_factor"):
        turnover = financials.get("annual_turnover_pct", 0)
        if turnover >= 0.12:
            combined_score = max(1, combined_score - 1)
            combined_cat = score_to_cat[combined_score]
            turnover_adj = f"Turnover {turnover:.0%} >= 12% — upgraded 1 notch"
        elif turnover >= 0.10:
            turnover_adj = f"Turnover {turnover:.0%} at 10% — neutral (validated by audited history)"

    # Principal sweep adjustment
    sweep_adj = ""
    if adj.get("principal_sweep_credit") and financials.get("principal_sweep", False):
        combined_score = max(1, combined_score - 1)
        combined_cat = score_to_cat[combined_score]
        sweep_adj = "Mandatory principal sweep — upgraded 1 notch"

    return {
        "sector": sector,
        "sector_adjusted": True,
        "methodology": f"Sector-specific: {override.get('primary_metric', 'dscr')}-based scoring",
        "dscr": {"value": dscr, "implied_rating": dscr_rating, "thresholds": dscr_thresholds},
        "days_cash_on_hand": {"value": days_cash, "implied_rating": dcoh_rating} if dcoh_thresholds else None,
        "debt_yield": {"value": debt_yield, "implied_rating": dy_rating} if dy_rating else None,
        "ltv": {"value": ltv, "implied_rating": ltv_rating} if ltv_rating else None,
        "combined_category": combined_cat,
        "combined_score": combined_score,
        "adjustments_applied": [a for a in [turnover_adj, sweep_adj] if a],
        "note": adj.get("description", ""),
    }


def score_moodys_financial(financials: dict) -> dict:
    """Score financial metrics per Moody's corporate methodology."""
    results = {}
    rating_order = ["Aaa", "Aa", "A", "Baa", "Ba", "B", "Caa", "Ca"]

    for metric, thresholds in MOODYS_FINANCIAL_METRICS.items():
        value = financials.get(metric, None)
        if value is None:
            results[metric] = {"value": None, "rating": None}
            continue

        assigned = "Ca"
        for rating in rating_order:
            bounds = thresholds[rating]
            if "max" in bounds and "min" not in bounds:
                if value <= bounds["max"]:
                    assigned = rating
                    break
            elif "min" in bounds and "max" not in bounds:
                if value >= bounds["min"]:
                    assigned = rating
                    break
            elif "min" in bounds and "max" in bounds:
                if bounds["min"] <= value <= bounds["max"]:
                    assigned = rating
                    break
            # Special: for debt_to_ebitda, lower is better
            if metric == "debt_to_ebitda":
                if "max" in bounds and value <= bounds["max"]:
                    assigned = rating
                    break

        results[metric] = {"value": value, "implied_rating": assigned}

    return results


def get_structuring_targets(target_rating: str) -> dict:
    """Given a target rating, return the structural parameters needed."""
    rating_key = target_rating.rstrip("+-").replace("+", "").replace("-", "")
    if rating_key not in STRUCTURING_CRITERIA["dscr_by_rating"]:
        rating_key = "BBB"

    return {
        "target_rating": target_rating,
        "min_dscr": STRUCTURING_CRITERIA["dscr_by_rating"][rating_key]["min"],
        "typical_dscr": STRUCTURING_CRITERIA["dscr_by_rating"][rating_key]["typical"],
        "min_equity": STRUCTURING_CRITERIA["equity_contribution_by_rating"][rating_key]["min_pct"],
        "dsrf_sizing": STRUCTURING_CRITERIA["dsrf_sizing"]["standard"],
        "covenant_package": STRUCTURING_CRITERIA["covenant_thresholds"].get(
            "investment_grade" if rating_key in ("AAA", "AA", "A", "BBB") else "high_yield"
        ),
        "call_protection": STRUCTURING_CRITERIA["call_protection_norms"].get(
            "investment_grade_muni" if rating_key in ("AAA", "AA", "A", "BBB") else "high_yield_corporate"
        ),
    }
