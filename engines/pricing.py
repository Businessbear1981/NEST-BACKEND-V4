"""
NEST PricingEngine — Silo 7
S&P DJI Fixed Income Index Mathematics (March 2025)

Implements the 7 core equations from the published methodology.
Every equation number in comments matches the S&P DJI document exactly.
Deferred equations (9, 11, 13-16, 21) are stubbed behind feature flags.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date
import math


# ── Day Count Conventions ────────────────────────────────────
def day_count_fraction(start: date, end: date, convention: str = "30/360") -> float:
    """Compute day count fraction between two dates."""
    if convention == "ACT/360":
        return (end - start).days / 360
    elif convention == "ACT/365":
        return (end - start).days / 365
    elif convention == "ACT/ACT":
        return (end - start).days / 365.25
    else:  # 30/360
        d1 = min(start.day, 30)
        d2 = min(end.day, 30) if d1 == 30 else end.day
        return (360 * (end.year - start.year) + 30 * (end.month - start.month) + (d2 - d1)) / 360


# ── Accrued Interest ─────────────────────────────────────────
def accrued_interest(coupon_rate: float, par: float,
                     last_coupon_date: date, settlement_date: date,
                     frequency: int = 2, convention: str = "30/360") -> float:
    """Calculate accrued interest on a bond."""
    period_coupon = coupon_rate * par / frequency
    dcf = day_count_fraction(last_coupon_date, settlement_date, convention)
    return period_coupon * dcf * frequency


# ── S&P DJI Eq. 17: Market Value ─────────────────────────────
def market_value(par: float, clean_price: float, ai: float,
                 fx_rate: float = 1.0) -> float:
    """
    MV = PAR * (P + AI) / 100 * FX          (Eq. 17)

    par:         Par amount outstanding
    clean_price: Market quoted price (% of par)
    ai:          Accrued interest (% of par)
    fx_rate:     FX conversion rate (1.0 for USD)
    """
    return par * (clean_price + ai) / 100 * fx_rate


# ── S&P DJI Eq. 8: Interest Return ──────────────────────────
def interest_return(ai_today: float, ai_yesterday: float,
                    coupon_payment: float, dirty_price_yesterday: float) -> float:
    """
    IR = (AI_t - AI_{t-1} + Cpn_t) / DirtyPrice_{t-1}    (Eq. 8)

    ai_today:              Accrued interest today (per 100 par)
    ai_yesterday:          Accrued interest yesterday (per 100 par)
    coupon_payment:        Coupon paid today (per 100 par), 0 if no payment
    dirty_price_yesterday: Clean price + accrued interest yesterday
    """
    if dirty_price_yesterday == 0:
        return 0.0
    return (ai_today - ai_yesterday + coupon_payment) / dirty_price_yesterday


# ── S&P DJI Eq. 10: Price Return ────────────────────────────
def price_return(clean_price_today: float, clean_price_yesterday: float,
                 dirty_price_yesterday: float, fx_return: float = 0.0) -> float:
    """
    PR = (CleanPrice_t - CleanPrice_{t-1} - FX_return) / DirtyPrice_{t-1}    (Eq. 10)

    clean_price_today:     Market quoted price today (no AI)
    clean_price_yesterday: Market quoted price yesterday (no AI)
    dirty_price_yesterday: Price + AI yesterday
    fx_return:             FX-related return component (0 for USD bonds)
    """
    if dirty_price_yesterday == 0:
        return 0.0
    return (clean_price_today - clean_price_yesterday - fx_return) / dirty_price_yesterday


# ── S&P DJI Eq. 7: Total Return ─────────────────────────────
def total_return(ir: float, pr: float) -> float:
    """
    TR = IR + PR    (Eq. 7)
    """
    return ir + pr


# ── S&P DJI Eq. 12: Total Unhedged Return ───────────────────
def total_unhedged_return(local_return: float,
                          fx_today: float, fx_yesterday: float) -> float:
    """
    TR_UH = (1 + R_L) * (1 + (FX_t - FX_{t-1}) / FX_{t-1}) - 1    (Eq. 12)

    local_return:  Total local currency return
    fx_today:      Spot FX rate today
    fx_yesterday:  Spot FX rate yesterday
    """
    if fx_yesterday == 0:
        return local_return
    fx_ret = (fx_today - fx_yesterday) / fx_yesterday
    return (1 + local_return) * (1 + fx_ret) - 1


# ── S&P DJI Eq. 20: Weight ──────────────────────────────────
def security_weight(amv_i: float, total_amv: float) -> float:
    """
    weight_i = AMV_i / Σ AMV_j    (Eq. 20)

    amv_i:     Adjusted market value of security i
    total_amv: Sum of all adjusted market values in the index
    """
    if total_amv == 0:
        return 0.0
    return amv_i / total_amv


# ── S&P DJI Eq. 22: Hedge-Adjusted Yield ────────────────────
def hedge_adjusted_yield(yield_local: float, forward_rate_30d: float,
                         fx_spot: float) -> float:
    """
    Hedge adjusted yield = Yield + (FF_{0,30} / FX_t - 1) * 12    (Eq. 22)

    yield_local:      Index-weighted yield from pro-forma universe
    forward_rate_30d: 30-day forward rate (30/360 convention)
    fx_spot:          Current FX spot rate
    """
    if fx_spot == 0:
        return yield_local
    return yield_local + (forward_rate_30d / fx_spot - 1) * 12


# ── Derived Metrics (not in S&P DJI doc, standard fixed income) ──

def duration_macaulay(coupon_rate: float, ytm: float, maturity_years: float,
                      frequency: int = 2, par: float = 100) -> float:
    """Macaulay duration — weighted average time to receive cash flows."""
    if ytm == 0:
        return maturity_years
    c = coupon_rate * par / frequency
    n = int(maturity_years * frequency)
    y = ytm / frequency
    pv_sum = 0.0
    wpv_sum = 0.0
    for i in range(1, n + 1):
        t = i / frequency
        pv = c / (1 + y) ** i
        pv_sum += pv
        wpv_sum += t * pv
    # Add principal
    pv_principal = par / (1 + y) ** n
    pv_sum += pv_principal
    wpv_sum += (n / frequency) * pv_principal
    return wpv_sum / pv_sum if pv_sum > 0 else 0


def duration_modified(mac_duration: float, ytm: float, frequency: int = 2) -> float:
    """Modified duration = Macaulay / (1 + ytm/freq)."""
    return mac_duration / (1 + ytm / frequency)


def convexity(coupon_rate: float, ytm: float, maturity_years: float,
              frequency: int = 2, par: float = 100) -> float:
    """Bond convexity — second derivative of price w.r.t. yield."""
    c = coupon_rate * par / frequency
    n = int(maturity_years * frequency)
    y = ytm / frequency
    conv_sum = 0.0
    price = 0.0
    for i in range(1, n + 1):
        pv = c / (1 + y) ** i
        price += pv
        conv_sum += pv * i * (i + 1)
    pv_principal = par / (1 + y) ** n
    price += pv_principal
    conv_sum += pv_principal * n * (n + 1)
    if price == 0:
        return 0
    return conv_sum / (price * (1 + y) ** 2 * frequency ** 2)


def dv01(modified_dur: float, price: float, par: float = 100) -> float:
    """Dollar value of a basis point = ModDur * Price * 0.0001."""
    return modified_dur * (price / 100) * par * 0.0001


def spread_to_benchmark(bond_ytm: float, benchmark_ytm: float) -> float:
    """Spread in basis points."""
    return (bond_ytm - benchmark_ytm) * 10000


def yield_to_worst(ytm: float, call_yields: list) -> float:
    """YTW = min of YTM and all yield-to-call values."""
    all_yields = [ytm] + call_yields
    return min(all_yields) if all_yields else ytm


# ── Index Eligibility (from S&P 500 Bond Index Methodology, Aug 2024) ──

RATING_ORDER = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
                "BBB+", "BBB", "BBB-",
                "BB+", "BB", "BB-", "B+", "B", "B-",
                "CCC+", "CCC", "CCC-", "CC", "C", "D"]

def is_investment_grade(rating: str) -> bool:
    """IG floor: BBB-/Baa3/BBB- (lowest of S&P/Moody's/Fitch)."""
    try:
        return RATING_ORDER.index(rating) <= RATING_ORDER.index("BBB-")
    except ValueError:
        return False

def is_index_eligible(par_outstanding: float, rating: str,
                      maturity_months: float, currency: str = "USD",
                      country: str = "US", is_convertible: bool = False,
                      is_floating: bool = False) -> dict:
    """
    Check S&P 500 Bond Index eligibility per Aug 2024 methodology.
    Returns dict with eligible flag + reasons.
    """
    reasons = []
    ig = is_investment_grade(rating)
    min_par = 250_000_000 if ig else 100_000_000

    if par_outstanding < min_par:
        reasons.append(f"Par ${par_outstanding:,.0f} below min ${min_par:,.0f}")
    if maturity_months < 1:
        reasons.append("Maturity < 1 month")
    if currency != "USD":
        reasons.append(f"Currency {currency} — must be USD")
    if country != "US":
        reasons.append(f"Country {country} — must be US")
    if is_convertible:
        reasons.append("Convertible bonds excluded")
    if is_floating:
        reasons.append("Floating-rate excluded")
    if rating == "D":
        reasons.append("Defaulted — excluded")

    return {
        "eligible": len(reasons) == 0,
        "investment_grade": ig,
        "rating": rating,
        "reasons": reasons,
    }


# ── Full Bond Pricing Output ─────────────────────────────────

def price_bond(par: float, clean_price: float, coupon_rate: float,
               ytm: float, maturity_years: float, frequency: int = 2,
               last_coupon_date: date = None, settlement_date: date = None,
               fx_rate: float = 1.0, benchmark_ytm: float = 0.0,
               swap_rate: float = 0.0, convention: str = "30/360",
               rating: str = "BBB") -> dict:
    """
    Full pricing output for a single bond.
    Maps to PricingEngine output schema in build brief Section 3.4.
    """
    # Accrued interest
    if last_coupon_date and settlement_date:
        ai = accrued_interest(coupon_rate, 100, last_coupon_date, settlement_date, frequency, convention)
    else:
        ai = 0.0

    dirty = clean_price + ai
    mv = market_value(par, clean_price, ai, fx_rate)

    # Derived metrics
    mac_dur = duration_macaulay(coupon_rate, ytm, maturity_years, frequency)
    mod_dur = duration_modified(mac_dur, ytm, frequency)
    conv = convexity(coupon_rate, ytm, maturity_years, frequency)
    dv = dv01(mod_dur, dirty, par)

    spread_tsy = spread_to_benchmark(ytm, benchmark_ytm)
    spread_swap = spread_to_benchmark(ytm, swap_rate)

    return {
        "par_outstanding": round(par),
        "clean_price": round(clean_price, 4),
        "accrued_interest": round(ai, 4),
        "dirty_price": round(dirty, 4),
        "fx_rate": fx_rate,
        "market_value": round(mv, 2),
        "ytm": round(ytm, 6),
        "duration": round(mac_dur, 4),
        "modified_duration": round(mod_dur, 4),
        "convexity": round(conv, 4),
        "dv01": round(dv, 2),
        "spread_to_treasury_bps": round(spread_tsy, 1),
        "spread_to_swap_bps": round(spread_swap, 1),
        "investment_grade": is_investment_grade(rating),
        "rating": rating,
        "day_count_convention": convention,
        "valuation_date": datetime.utcnow().isoformat(),
    }
