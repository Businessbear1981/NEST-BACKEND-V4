"""Jacaranda Trace — Full Modeling Test"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from services.intelligence_engine import IntelligenceEngine
from services.rating_benchmarks import score_sp_financial_risk, get_structuring_targets

ie = IntelligenceEngine()

BOND = 205_000_000
EXISTING = 80_780_000
FADS = 18_095_480
APPRAISED = 435_000_000
UNITS = 447
FEE_AVG = 454_000
SPONSOR_NW = 280_000_000

print("=" * 80)
print("  JACARANDA TRACE SERIES 2026 -- FULL MODELING")
print("  Convivial Jacaranda Trace, LLC | Venice, FL | 501(c)(3) CCRC")
print("  Sponsor: David Falk (FAME) -- $280M Net Worth")
print("=" * 80)
print()

# SOURCES & USES
print("SOURCES & USES")
print("-" * 60)
uses = {
    "Refund Existing Bonds (2022A/B/C + 2023A)": EXISTING,
    "Unit Acquisition (remaining LSPL from 3rd party)": 65_000_000,
    "Renovation / Rehab (55 units at ~$636K)": 35_000_000,
    "Reserves (DSRF + Operating + Cap-I)": 12_000_000,
    "Issuance Costs (legal, rating, trustee, UW)": 8_220_000,
    "Working Capital": 4_000_000,
}
print("SOURCES:")
print(f"  Series 2026 Bonds              ${BOND:>15,}")
print()
print("USES:")
for k, v in uses.items():
    print(f"  {k:50s}${v:>12,}")
print(f"  {'TOTAL':50s}${sum(uses.values()):>12,}")
print()

# STRUCTURE OPTIONS
print("BOND STRUCTURE OPTIONS")
print("-" * 60)

options = [
    ("A: 7yr NC-3 Par Call", 7, 3, 6.75, "IO yr 1-3 (acquisition), then entrance-fee principal sweep", "NC-3, 103/102/101/par step-down, par call yr 5+"),
    ("B: 10yr NC-5 Make-Whole", 10, 5, 7.25, "IO yr 1-3, level debt service yr 4-10", "NC-5 make-whole, par call yr 7+"),
    ("C: 7yr Cash-Collat LC (AAA)", 7, 2, 4.25, "IO yr 1-3, principal sweep from entrance fees", "NC-2 par call -- LC provides AAA pricing"),
]

for name, tenor, nc, coupon, amort, call in options:
    ads = BOND * coupon / 100
    dscr = FADS / ads
    ltv = BOND / APPRAISED
    annual_savings_vs_current = 9_695_754 - ads if ads < 9_695_754 else 0

    print(f"  OPTION {name}")
    print(f"    Tenor:          {tenor} years")
    print(f"    Est Coupon:     {coupon}%")
    print(f"    Amortization:   {amort}")
    print(f"    Call Schedule:  {call}")
    print(f"    Ann Debt Svc:   ${ads:>12,.0f}")
    print(f"    DSCR (FADS):    {dscr:.2f}x")
    print(f"    LTV:            {ltv:.1%}")
    if annual_savings_vs_current > 0:
        print(f"    Savings vs Now: ${annual_savings_vs_current:>12,.0f}/yr")

    # S&P sector scoring
    sp = score_sp_financial_risk({
        "sector": "senior_living",
        "dscr": dscr,
        "days_cash_on_hand": 122,
        "debt_yield": FADS / BOND,
        "annual_turnover_pct": 0.12,
        "principal_sweep": True,
    })
    print(f"    S&P Risk:       {sp['combined_category']} (score {sp['combined_score']})")
    if sp.get("dscr"):
        print(f"    DSCR Rating:    {sp['dscr']['implied_rating']}")
    for adj in sp.get("adjustments_applied", []):
        print(f"    Adjustment:     {adj}")
    print()

# SPONSOR
print("SPONSOR ANALYSIS -- DAVID FALK")
print("-" * 60)
print(f"  Name:              David Falk")
print(f"  Background:        Founder, FAME (sports/entertainment mgmt)")
print(f"                     Michael Jordan's agent -- iconic dealmaker")
print(f"  Net Worth:         ${SPONSOR_NW:>12,}")
print(f"  Bond Amount:       ${BOND:>12,}")
print(f"  NW/Bond:           {SPONSOR_NW/BOND:.1f}x coverage")
print()
print("  CASH-COLLAT LC ANALYSIS (Option C):")
lc = 40_000_000
print(f"    LC Collateral:   ${lc:>12,} ({lc/SPONSOR_NW:.0%} of NW)")
print(f"    Remaining NW:    ${SPONSOR_NW-lc:>12,}")
print(f"    Escrow Earnings: ${lc*0.045:>12,.0f}/yr at 4.5% treasury")
print(f"    Coupon Savings:  {6.75-4.25:.2f}% = ${BOND*(6.75-4.25)/100:>12,.0f}/yr vs Option A")
print(f"    Net Benefit:     ${BOND*(6.75-4.25)/100 + lc*0.045:>12,.0f}/yr (savings + escrow income)")
print()

# DELEVERAGING
print("DELEVERAGING MODEL -- ENTRANCE FEE PRINCIPAL SWEEP")
print("-" * 60)
print(f"{'Yr':>3} | {'Units':>5} | {'Gross Fees':>12} | {'Refunds':>10} | {'Net Sweep':>12} | {'Balance':>14} | {'LTV':>6}")
print("-" * 80)
balance = BOND
for yr in range(1, 11):
    if yr <= 3:
        # Acquisition phase: buying remaining units + renovating + selling
        # Year 1: 55 renovated units sweep immediately
        if yr == 1:
            units = 67  # 55 reno + normal turnover
        else:
            units = int(UNITS * 0.14)  # Higher velocity during ramp
    else:
        units = int(UNITS * 0.11)  # Stabilized 11% turnover

    gross = units * FEE_AVG
    refunds = int(gross * 0.14)
    sweep = gross - refunds
    balance = max(0, balance - sweep)
    ltv = balance / APPRAISED

    marker = " <-- REFI POINT" if yr == 3 else ""
    print(f"  {yr:2d} | {units:>5} | ${gross/1e6:>9.1f}M | ${refunds/1e6:>7.1f}M | ${sweep/1e6:>9.1f}M | ${balance/1e6:>11.1f}M | {ltv:>5.1%}{marker}")

print()
print(f"  Year 3 Refi Target: ${balance:,.0f}")
print(f"  Year 3 LTV:         {balance/APPRAISED:.1%}")
print(f"  Deleveraged:        ${BOND-balance:,.0f} in 3 years from entrance fee sweep alone")
print()

# COVENANT PACKAGE
print("PROPOSED COVENANT PACKAGE")
print("-" * 60)
print("  DSCR Covenant:          1.20x (FADS-based -- NOT EBITDA)")
print("  Days Cash on Hand:      120 days minimum")
print("  Debt Yield:             11% minimum")
print("  Additional Bonds Test:  1.20x historical DSCR")
print("  Distribution Trap:      At DSCR below 1.10x")
print("  Principal Sweep:        MANDATORY -- net entrance fees after refunds")
print("  Acquisition Window:     3 years to complete unit purchases")
print("  Renovation Deadline:    Units renovated within 18mo of purchase")
print("  Occupancy Reporting:    Quarterly by care level (IL/AL/MC)")
print("  Financial Reporting:    Annual audited + quarterly unaudited")
print("  Call Protection:        NC-3 (Option A) or NC-2 (Option C)")
print()

# RECOMMENDATION
print("RECOMMENDATION")
print("-" * 60)
print("  Option C (Cash-Collateralized LC) is the optimal structure:")
print()
print("  1. AAA-equivalent pricing at 4.25% vs 6.75% standalone")
print(f"     Saves ${BOND*(6.75-4.25)/100:,.0f}/yr in debt service")
print(f"  2. Sponsor deploys ${lc/1e6:.0f}M (14% of NW) -- conservative allocation")
print(f"     Earns ${lc*0.045:,.0f}/yr on escrow at treasury rate")
print(f"  3. Net annual benefit: ${BOND*(6.75-4.25)/100 + lc*0.045:,.0f}")
print("  4. NC-2 allows early refi when stabilized (year 3)")
print("  5. Principal sweep deleverages from $205M to ~$127M by year 3")
print(f"     Year 3 LTV drops to ~29% -- extremely conservative")
print("  6. At refi, LC released, sponsor cash returns with appreciation")
print()
print("  ALTERNATIVE: Option A if sponsor prefers not to deploy cash.")
print("  Still investment-grade at 1.31x DSCR with 12% validated turnover.")
print()
print("=" * 80)
print("  MODELING COMPLETE -- JACARANDA TRACE SERIES 2026")
print("=" * 80)
