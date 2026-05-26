"""
MerlinAgent — M&A intelligence, target scoring, and deal structuring.

Responsibilities:
  - Score acquisition targets across 12 weighted dimensions
  - Run 3-level game theory analysis on targets
  - Build business plans via Claude API
  - Model IRR across 3x3 scenario matrix
  - Scan EDGAR for acquisition targets by NAICS
  - Orchestrate full deal analysis pipeline
  - Assess IPO readiness across 8 gateway dimensions
"""
import math
import random
from datetime import datetime

# Safe imports — all optional at runtime
try:
    from agents._claude import ask_claude
except ImportError:
    ask_claude = None

try:
    from services.edgar_scanner import edgar_scanner
except ImportError:
    edgar_scanner = None

try:
    from blockchain.nest_chain import chain
except ImportError:
    chain = None

try:
    from game_theory.engine import game_engine
except ImportError:
    game_engine = None

try:
    from services.data_connectors import EDGARPlugin
    jimmy_lee = EDGARPlugin()
except ImportError:
    jimmy_lee = None


# NAICS priority tiers for NEST acquisition strategy
# Tier 1: +8 score bonus | Tier 2: +4 bonus | Tier 3: +1 bonus
NAICS_PRIORITY = {
    "tier1": {
        "description": "Highest-conviction targets -- recurring revenue, essential services, fragmented markets ripe for roll-up",
        "codes": {
            # Essential facility/property services -- sticky contracts, low churn
            "561730": "Landscaping Services",
            "561720": "Janitorial / Commercial Cleaning",
            "561210": "Facilities Support Services",
            "561621": "Security Guard & Patrol Services",
            "561710": "Exterminating & Pest Control",
            # Essential trades -- licensed, recurring, impossible to offshore
            "238220": "Plumbing, Heating & AC Contractors",
            "238210": "Electrical Contractors",
            "238160": "Roofing Contractors",
            "238990": "Other Specialty Trade Contractors",
            "238130": "Framing Contractors",
            # Home & healthcare -- aging demographic tailwind
            "621610": "Home Health Care Services",
            "623110": "Nursing Care Facilities",
            "623210": "Assisted Living Facilities",
            "624120": "Services for the Elderly & Disabled",
            "624410": "Child Day Care Services",
            # Waste & environmental -- essential, regulation-moated
            "562111": "Solid Waste Collection",
            "562910": "Remediation Services",
            "562920": "Materials Recovery Facilities",
            # Auto repair -- fragmented, cash-flowing, recession-resilient
            "811111": "General Automotive Repair",
            "811121": "Automotive Body & Paint Repair",
            "811192": "Car Washes",
            # Staffing -- high volume, recurring, fragmented
            "561311": "Employment Placement Agencies",
            "561320": "Temporary Help Services",
            "561330": "Professional Employer Organizations",
            # Inspection / testing -- regulated, recurring certifications
            "541380": "Testing Laboratories",
            "541350": "Building Inspection Services",
        },
    },
    "tier2": {
        "description": "Strong adjacents -- scalable models with clear value-add thesis",
        "codes": {
            # Distribution / wholesale -- add logistics capability to roll-ups
            "423830": "Industrial Machinery & Equipment Wholesale",
            "423860": "Transportation Equipment & Supplies Wholesale",
            "423720": "Plumbing & Heating Equipment Wholesale",
            "424440": "Poultry & Poultry Products Wholesale",
            "424410": "General Line Grocery Wholesale",
            "424690": "Other Chemical & Allied Products Wholesale",
            # Trucking & logistics -- asset-backed, steady cash flow
            "484110": "General Freight Trucking (Local)",
            "484121": "General Freight Trucking (Long Distance, TL)",
            "484122": "General Freight Trucking (Long Distance, LTL)",
            "484220": "Specialized Freight - Refrigerated",
            "484230": "Specialized Freight - Other",
            "493110": "General Warehousing & Storage",
            "488490": "Other Support Activities for Road Transportation",
            # Professional services -- high margin, portable
            "541211": "CPA Firms (Audit & Tax)",
            "541213": "Tax Preparation Services",
            "541310": "Architectural Services",
            "541330": "Engineering Services",
            "541611": "General Management Consulting",
            "541612": "HR Consulting",
            "541620": "Environmental Consulting",
            "541690": "Other Scientific & Technical Consulting",
            # IT / technology services -- recurring SaaS or managed services
            "541511": "Custom Computer Programming Services",
            "541512": "Computer Systems Design Services",
            "541513": "Computer Facilities Management",
            "541519": "Other Computer Related Services",
            "518210": "Data Processing & Hosting Services",
            # Healthcare adjacent
            "621111": "Physician Offices",
            "621210": "Dentist Offices",
            "621340": "Physical, Occupational & Speech Therapist Offices",
            "621491": "HMO Medical Centers",
            "621498": "Other Outpatient Care Centers",
        },
    },
    "tier3": {
        "description": "Opportunistic -- asset-heavy, cyclical, or special-situation targets with turnaround potential",
        "codes": {
            # Construction -- lumpy but large deal sizes
            "236115": "New Single-Family Home Construction",
            "236116": "New Multifamily Housing Construction",
            "236210": "Industrial Building Construction",
            "236220": "Commercial & Institutional Building Construction",
            "237110": "Water & Sewer System Construction",
            "237130": "Power & Communication Line Construction",
            "237310": "Highway, Street & Bridge Construction",
            "237990": "Heavy Civil Construction (Other)",
            # Real estate / leasing
            "531110": "Lessors of Residential Buildings",
            "531120": "Lessors of Nonresidential Buildings",
            "531130": "Lessors of Miniwarehouses / Self-Storage",
            "531210": "Offices of Real Estate Agents & Brokers",
            "531311": "Residential Property Managers",
            "531312": "Nonresidential Property Managers",
            "531320": "Offices of Real Estate Appraisers",
            # Equipment & vehicle rental
            "532111": "Passenger Car Rental",
            "532120": "Truck, Utility Trailer & RV Rental",
            "532310": "General Rental Centers",
            "532411": "Commercial Air, Rail & Water Transport Equipment Rental",
            "532412": "Construction & Mining Equipment Rental",
            "532420": "Office Machinery & Equipment Rental",
            # Manufacturing -- light industrial with defensible niche
            "332311": "Prefabricated Metal Building Manufacturing",
            "332322": "Sheet Metal Work Manufacturing",
            "332710": "Machine Shops",
            "332720": "Turned Product & Screw, Nut & Bolt Manufacturing",
            "332999": "All Other Miscellaneous Fabricated Metal Products",
            "333120": "Construction Machinery Manufacturing",
            "333924": "Industrial Truck Manufacturing",
            "339112": "Surgical & Medical Instrument Manufacturing",
            "339113": "Surgical Appliance & Supplies Manufacturing",
            # Retail / auto dealers -- asset-backed, predictable floor plan
            "441110": "New Car Dealers",
            "441120": "Used Car Dealers",
            "441210": "Recreational Vehicle Dealers",
            "441222": "Boat Dealers",
            "447110": "Gasoline Stations with Convenience Stores",
            # Food service / hospitality -- roll-up candidates
            "722511": "Full-Service Restaurants",
            "722513": "Limited-Service Restaurants",
            "722514": "Cafeterias & Grill Buffets",
            "722515": "Snack & Nonalcoholic Beverage Bars",
            "721110": "Hotels & Motels",
            # Education / training
            "611519": "Other Technical & Trade Schools",
            "611610": "Fine Arts Schools",
            "611620": "Sports & Recreation Instruction",
            "611630": "Language Schools",
            "611691": "Exam Preparation & Tutoring",
            # Energy / utilities
            "221111": "Hydroelectric Power Generation",
            "221114": "Solar Electric Power Generation",
            "221115": "Wind Electric Power Generation",
            "221210": "Natural Gas Distribution",
            "221310": "Water Supply & Irrigation Systems",
            "221320": "Sewage Treatment Facilities",
        },
    },
}


class MerlinAgent:
    """M&A acquisition intelligence agent."""

    # Scoring dimensions and weights (12 dimensions, rebalanced to 100%)
    # Original 8 dimensions reduced proportionally (×0.72) to make room for 4 new ones
    SCORING_WEIGHTS = {
        "revenue_quality": 0.13,
        "margin_profile": 0.11,
        "owner_dependency": 0.10,
        "customer_concentration": 0.09,
        "growth_trajectory": 0.07,
        "defensibility": 0.07,
        "workforce_stability": 0.08,
        "asset_quality": 0.07,
        # New dimensions
        "regional_national_growth": 0.08,
        "revenue_diversification": 0.07,
        "scalability": 0.08,
        "syndicated_loan_signals": 0.05,
    }

    def __init__(self):
        self.analysis_cache = {}

    # ------------------------------------------------------------------ #
    #  TARGET SCORING (12 dimensions)                                     #
    # ------------------------------------------------------------------ #

    def score_target(self, target: dict) -> dict:
        """
        Score an acquisition target on 12 weighted dimensions (0-100 each).

        target: {name, revenue, ebitda, ebitda_margin, revenue_growth,
                 top_customer_pct, owner_involved, employee_tenure_avg,
                 recurring_revenue_pct, asset_age_years, patents, contracts,
                 sector, naics,
                 market_growth_pct, regional_growth_factor,
                 revenue_streams, geographic_markets,
                 tech_enabled, repeatable_process, capacity_utilization_pct,
                 has_syndicated_debt, recent_refinancing, announced_equity_raise}
        """
        scores = {}

        # 1. Revenue quality — recurring revenue, diversification
        recurring_pct = target.get("recurring_revenue_pct", 0.20)
        revenue = target.get("revenue", 0)
        scores["revenue_quality"] = min(100, recurring_pct * 100 + (10 if revenue > 5_000_000 else 0))

        # 2. Margin profile
        margin = target.get("ebitda_margin", 0.10)
        if margin >= 0.25:
            scores["margin_profile"] = 95
        elif margin >= 0.18:
            scores["margin_profile"] = 80
        elif margin >= 0.12:
            scores["margin_profile"] = 60
        elif margin >= 0.08:
            scores["margin_profile"] = 40
        else:
            scores["margin_profile"] = 20

        # 3. Owner dependency (lower is better)
        owner_involved = target.get("owner_involved", True)
        if not owner_involved:
            scores["owner_dependency"] = 90
        else:
            mgmt_depth = target.get("management_depth", 1)
            scores["owner_dependency"] = min(80, 30 + mgmt_depth * 15)

        # 4. Customer concentration (lower top-customer % is better)
        top_cust = target.get("top_customer_pct", 0.30)
        scores["customer_concentration"] = max(10, 100 - top_cust * 200)

        # 5. Growth trajectory
        growth = target.get("revenue_growth", 0.0)
        if growth >= 0.15:
            scores["growth_trajectory"] = 90
        elif growth >= 0.08:
            scores["growth_trajectory"] = 70
        elif growth >= 0.02:
            scores["growth_trajectory"] = 50
        elif growth >= -0.05:
            scores["growth_trajectory"] = 30
        else:
            scores["growth_trajectory"] = 15

        # 6. Defensibility — patents, long-term contracts, licenses
        patents = target.get("patents", 0)
        contracts = target.get("contracts", 0)
        licenses = target.get("licenses", 0)
        def_score = min(100, patents * 15 + contracts * 10 + licenses * 12 + 20)
        scores["defensibility"] = def_score

        # 7. Workforce stability
        tenure_avg = target.get("employee_tenure_avg", 3.0)
        turnover = target.get("turnover_rate", 0.20)
        scores["workforce_stability"] = min(100, tenure_avg * 12 + (1 - turnover) * 40)

        # 8. Asset quality
        asset_age = target.get("asset_age_years", 5)
        if asset_age <= 3:
            scores["asset_quality"] = 85
        elif asset_age <= 7:
            scores["asset_quality"] = 65
        elif asset_age <= 12:
            scores["asset_quality"] = 45
        else:
            scores["asset_quality"] = 25

        # 9. Regional/National Growth — is the target in a growing market?
        market_growth = target.get("market_growth_pct", 5.0)
        regional_factor = target.get("regional_growth_factor", 1.0)
        effective_growth = market_growth * regional_factor
        if effective_growth >= 15:
            scores["regional_national_growth"] = 95
        elif effective_growth >= 10:
            scores["regional_national_growth"] = 80
        elif effective_growth >= 5:
            scores["regional_national_growth"] = 60
        elif effective_growth >= 0:
            scores["regional_national_growth"] = 40
        else:
            scores["regional_national_growth"] = 15

        # 10. Revenue Diversification — how diversified is the revenue?
        rev_streams = target.get("revenue_streams", 1)
        geo_markets = target.get("geographic_markets", 1)
        if rev_streams >= 5 and geo_markets >= 3:
            scores["revenue_diversification"] = 90
        elif rev_streams >= 3:
            scores["revenue_diversification"] = 70
        elif rev_streams >= 2:
            scores["revenue_diversification"] = 50
        else:
            scores["revenue_diversification"] = 25

        # 11. Scalability — can this business scale without proportional cost increase?
        tech_enabled = target.get("tech_enabled", False)
        repeatable = target.get("repeatable_process", False)
        cap_util = target.get("capacity_utilization_pct", 80.0)
        if tech_enabled and repeatable and cap_util < 70:
            scores["scalability"] = 95
        elif tech_enabled and repeatable:
            scores["scalability"] = 80
        elif repeatable:
            scores["scalability"] = 60
        else:
            scores["scalability"] = 30

        # 12. Syndicated Loan Signals — evidence of active syndicated lending / refinancing
        has_syndicated = target.get("has_syndicated_debt", False)
        recent_refi = target.get("recent_refinancing", False)
        equity_raise = target.get("announced_equity_raise", False)
        if equity_raise:
            scores["syndicated_loan_signals"] = 95  # hot signal
        elif recent_refi:
            scores["syndicated_loan_signals"] = 75
        elif has_syndicated:
            scores["syndicated_loan_signals"] = 60
        else:
            scores["syndicated_loan_signals"] = 30

        # Weighted composite
        composite = sum(
            scores[dim] * weight
            for dim, weight in self.SCORING_WEIGHTS.items()
        )

        # NAICS tier bonus
        naics = target.get("naics", "")
        tier = "none"
        tier_bonus = 0
        for t_name, t_data in NAICS_PRIORITY.items():
            if naics in t_data["codes"]:
                tier = t_name
                tier_bonus = {"tier1": 8, "tier2": 4, "tier3": 1}.get(t_name, 0)
                break

        composite = min(100, composite + tier_bonus)

        # Recommendation
        if composite >= 75:
            recommendation = "STRONG_BUY"
        elif composite >= 60:
            recommendation = "BUY"
        elif composite >= 45:
            recommendation = "REVIEW"
        else:
            recommendation = "PASS"

        return {
            "target_name": target.get("name", "Unknown"),
            "composite_score": round(composite, 1),
            "dimension_scores": {k: round(v, 1) for k, v in scores.items()},
            "naics_tier": tier,
            "tier_bonus": tier_bonus,
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------ #
    #  GAME THEORY INTEGRATION                                            #
    # ------------------------------------------------------------------ #

    def run_game_theory(self, target: dict, market_data: dict = None,
                        competitors: list = None, history: list = None) -> dict:
        """Run full 3-level game theory analysis on a target."""
        if game_engine is None:
            return {"error": "game_theory.engine not available"}

        secondary = {
            "market_data": market_data or {"signals": {}},
            "competitors": competitors or [],
            "nest_params": {"max_multiple": 8.0, "synergy_pct": 0.12, "cost_of_capital": 0.10},
        }

        result = game_engine.run_full_analysis(
            analysis_type="acquisition",
            primary_data=target,
            secondary_data=secondary,
            history=history or [],
        )

        # Record on chain
        if chain is not None:
            try:
                chain.record_ma_analysis(
                    company_name=target.get("name", "unknown"),
                    analysis_data={"composite": result.get("synthesis", {}).get("composite_score")},
                    game_theory_result=result.get("synthesis", {}).get("recommendation"),
                    level="full",
                )
            except Exception:
                pass

        return result

    # ------------------------------------------------------------------ #
    #  BUSINESS PLAN (Claude API)                                         #
    # ------------------------------------------------------------------ #

    def build_business_plan(self, target: dict, score_result: dict,
                             game_theory_result: dict = None) -> dict:
        """Generate acquisition business plan via Claude API."""
        if ask_claude is None:
            return {"error": "Claude API not available", "plan": None}

        prompt = f"""You are MERLIN, NEST's M&A intelligence agent. Build a concise acquisition
business plan for the following target:

Company: {target.get('name', 'Unknown')}
Sector: {target.get('sector', 'Unknown')}
Revenue: ${target.get('revenue', 0):,.0f}
EBITDA: ${target.get('ebitda', 0):,.0f}
EBITDA Margin: {target.get('ebitda_margin', 0):.1%}

Acquisition Score: {score_result.get('composite_score', 'N/A')}/100
Recommendation: {score_result.get('recommendation', 'N/A')}

Game Theory Recommendation: {game_theory_result.get('synthesis', {}).get('recommendation', 'N/A') if game_theory_result else 'N/A'}

Provide:
1. Executive Summary (3 sentences)
2. Investment Thesis (3 bullet points)
3. Value Creation Plan (100-day, Year 1, Year 2-3)
4. Key Risks and Mitigants (top 3)
5. Recommended Deal Structure (purchase price range, financing mix, earnout terms)
"""
        try:
            response = ask_claude(prompt, system="You are MERLIN, a sharp M&A analyst. Be concise and specific.")
            return {"plan": response, "generated_at": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"error": str(e), "plan": None}

    # ------------------------------------------------------------------ #
    #  IRR MODELING (3x3 scenario matrix)                                 #
    # ------------------------------------------------------------------ #

    def model_irr(self, target: dict, hold_years: int = 5) -> dict:
        """
        3x3 IRR matrix: entry multiple x exit multiple x growth rate.

        Rows: entry multiple (low, base, high)
        Cols: exit multiple (contraction, stable, expansion)
        Layers: growth (bear, base, bull)
        """
        ebitda = target.get("ebitda", 1_000_000)
        growth_scenarios = {"bear": 0.02, "base": 0.07, "bull": 0.12}
        entry_multiples = {"low": 4.5, "base": 6.0, "high": 7.5}
        exit_multiples = {"contraction": 4.0, "stable": 6.0, "expansion": 8.0}

        matrix = {}
        for g_label, g_rate in growth_scenarios.items():
            matrix[g_label] = {}
            for e_label, entry_mult in entry_multiples.items():
                matrix[g_label][e_label] = {}
                entry_price = ebitda * entry_mult
                for x_label, exit_mult in exit_multiples.items():
                    future_ebitda = ebitda * ((1 + g_rate) ** hold_years)
                    exit_price = future_ebitda * exit_mult
                    # Add cumulative free cash flow (assume 60% of EBITDA)
                    total_fcf = sum(
                        ebitda * ((1 + g_rate) ** y) * 0.60
                        for y in range(1, hold_years + 1)
                    )
                    total_return = exit_price + total_fcf
                    if entry_price > 0:
                        irr = (total_return / entry_price) ** (1 / hold_years) - 1
                    else:
                        irr = 0.0
                    moic = total_return / entry_price if entry_price > 0 else 0.0

                    matrix[g_label][e_label][x_label] = {
                        "irr": round(irr, 4),
                        "irr_pct": f"{irr:.1%}",
                        "moic": round(moic, 2),
                        "entry_price": round(entry_price, 0),
                        "exit_price": round(exit_price, 0),
                    }

        # Find base case
        base_case = matrix["base"]["base"]["stable"]

        return {
            "target_name": target.get("name", "Unknown"),
            "hold_years": hold_years,
            "matrix": matrix,
            "base_case_irr": base_case["irr_pct"],
            "base_case_moic": base_case["moic"],
            "meets_hurdle": base_case["irr"] >= 0.20,
            "hurdle_rate": "20%",
        }

    # ------------------------------------------------------------------ #
    #  EDGAR SCANNER                                                      #
    # ------------------------------------------------------------------ #

    def scan_edgar_for_targets(self, naics_codes: list = None, min_revenue: float = 2_000_000,
                                max_revenue: float = 50_000_000) -> dict:
        """
        Scan EDGAR (via Jimmy Lee service) for acquisition targets by NAICS.
        Falls back to synthetic data if service unavailable.
        """
        if naics_codes is None:
            naics_codes = list(NAICS_PRIORITY["tier1"]["codes"].keys())

        targets = []

        if jimmy_lee is not None:
            try:
                for code in naics_codes:
                    sector_name = ""
                    for tier_data in NAICS_PRIORITY.values():
                        if code in tier_data["codes"]:
                            sector_name = tier_data["codes"][code]
                            break
                    if not sector_name:
                        continue
                    result = jimmy_lee.execute(company=sector_name, filing_type="10-K")
                    if result.get("success") and result.get("filings"):
                        for filing in result["filings"]:
                            targets.append({
                                "name": filing.get("name", "Unknown"),
                                "naics": code,
                                "sector": sector_name,
                                "source": "edgar_filing",
                                "form": filing.get("form", ""),
                                "filing_date": filing.get("date", ""),
                                "url": filing.get("url", ""),
                            })
            except Exception:
                pass

        # If no external results, generate synthetic scan results
        if not targets:
            sectors = ["Landscaping", "HVAC", "Plumbing", "Janitorial", "Auto Repair",
                        "Electrical", "Waste Collection", "Home Health"]
            for i, code in enumerate(naics_codes[:8]):
                sector = sectors[i % len(sectors)]
                rev = random.uniform(min_revenue, max_revenue)
                margin = random.uniform(0.08, 0.28)
                targets.append({
                    "name": f"{sector} Co #{i + 1}",
                    "naics": code,
                    "sector": sector,
                    "revenue": round(rev, 0),
                    "ebitda": round(rev * margin, 0),
                    "ebitda_margin": round(margin, 3),
                    "ev_usd": round(rev * margin * random.uniform(4, 7), 0),
                    "source": "synthetic_scan",
                })

        return {
            "scan_date": datetime.utcnow().isoformat(),
            "naics_codes_searched": naics_codes,
            "revenue_range": [min_revenue, max_revenue],
            "targets_found": len(targets),
            "targets": targets,
        }

    # ------------------------------------------------------------------ #
    #  FULL ANALYSIS PIPELINE                                             #
    # ------------------------------------------------------------------ #

    def run_full_analysis(self, target: dict, market_data: dict = None,
                           competitors: list = None, history: list = None,
                           include_business_plan: bool = False) -> dict:
        """
        Orchestrate complete analysis: score + game theory + IRR + optional plan.
        """
        result = {
            "target": target.get("name", "Unknown"),
            "analysis_started": datetime.utcnow().isoformat(),
        }

        # Step 1: Score
        score = self.score_target(target)
        result["scoring"] = score

        # Step 2: Game theory
        gt = self.run_game_theory(target, market_data, competitors, history)
        result["game_theory"] = gt

        # Step 3: IRR model
        irr = self.model_irr(target)
        result["irr_model"] = irr

        # Step 4: Business plan (optional, requires Claude API)
        if include_business_plan:
            plan = self.build_business_plan(target, score, gt)
            result["business_plan"] = plan

        # Composite verdict
        score_val = score.get("composite_score", 50)
        gt_composite = gt.get("synthesis", {}).get("composite_score", 0.5)
        irr_meets = irr.get("meets_hurdle", False)

        if score_val >= 70 and gt_composite >= 0.55 and irr_meets:
            verdict = "STRONG_PROCEED"
        elif score_val >= 55 and gt_composite >= 0.40:
            verdict = "PROCEED_WITH_DILIGENCE"
        elif score_val >= 40:
            verdict = "FURTHER_REVIEW"
        else:
            verdict = "PASS"

        result["verdict"] = verdict
        result["analysis_completed"] = datetime.utcnow().isoformat()

        # Cache
        self.analysis_cache[target.get("name", "unknown")] = result

        # Record on chain
        if chain is not None:
            try:
                chain.record_ma_analysis(
                    company_name=target.get("name", "unknown"),
                    analysis_data={"score": score_val, "irr_meets_hurdle": irr_meets},
                    game_theory_result=verdict,
                    level="full_pipeline",
                )
            except Exception:
                pass

        return result


    # ------------------------------------------------------------------ #
    #  IPO READINESS ASSESSMENT                                           #
    # ------------------------------------------------------------------ #

    def assess_ipo_readiness(self, target: dict) -> dict:
        """Assess target's readiness for IPO based on institutional benchmarks."""
        gates = {}

        revenue = target.get("revenue_usd", 0)
        ebitda = target.get("ebitda_usd", 0)
        margin = target.get("ebitda_margin_pct", 0)
        growth = target.get("revenue_growth_pct", 0)

        # 1. Revenue Scale (min $100M for serious IPO, $250M+ ideal)
        gates["revenue_scale"] = {
            "score": min(100, max(0, int((revenue / 250_000_000) * 100))),
            "benchmark": "$250M+ revenue (ideal), $100M minimum",
            "current": f"${revenue / 1e6:.0f}M",
            "gap": f"${max(0, (100_000_000 - revenue)) / 1e6:.0f}M to minimum" if revenue < 100_000_000 else "Meets minimum",
        }

        # 2. Revenue Growth (20%+ YoY for growth IPO, 10%+ for value)
        gates["revenue_growth"] = {
            "score": min(100, max(0, int(growth * 4))),  # 25% growth = 100
            "benchmark": "20%+ YoY (growth), 10%+ (value)",
            "current": f"{growth:.1f}%",
            "gap": f"Need {max(0, 10 - growth):.1f}pp more" if growth < 10 else "On track",
        }

        # 3. Profitability (positive EBITDA, 15%+ margin preferred)
        gates["profitability"] = {
            "score": min(100, max(0, int(margin * 5))),  # 20% margin = 100
            "benchmark": "EBITDA positive, 15%+ margin preferred",
            "current": f"{margin:.1f}% EBITDA margin",
            "gap": "Needs profitability" if margin <= 0 else f"{'Strong' if margin >= 15 else 'Improving'}",
        }

        # 4. Audit Readiness (SOX compliance, Big 4 auditor, 3yr audited financials)
        has_auditor = target.get("has_big4_auditor", False)
        years_audited = target.get("years_audited", 0)
        gates["audit_readiness"] = {
            "score": (40 if has_auditor else 0) + min(60, years_audited * 20),
            "benchmark": "Big 4 auditor, 3+ years audited financials, SOX-ready",
            "current": f"{'Big 4' if has_auditor else 'No Big 4'}, {years_audited}yr audited",
            "gap": "Need Big 4 auditor" if not has_auditor else ("Need 3yr history" if years_audited < 3 else "Ready"),
        }

        # 5. Corporate Governance (independent board, committees, C-suite depth)
        board_independent = target.get("independent_board_members", 0)
        has_cfo = target.get("has_experienced_cfo", False)
        gates["governance"] = {
            "score": min(100, board_independent * 25 + (30 if has_cfo else 0)),
            "benchmark": "3+ independent directors, experienced CFO, audit/comp committees",
            "current": f"{board_independent} independent directors, {'CFO' if has_cfo else 'no CFO'}",
            "gap": f"Need {max(0, 3 - board_independent)} more independent directors" if board_independent < 3 else "Strong",
        }

        # 6. Market Position (TAM, market share, competitive moat)
        tam = target.get("total_addressable_market_usd", 0)
        market_share = target.get("market_share_pct", 0)
        gates["market_position"] = {
            "score": min(100, int((tam / 5_000_000_000) * 50) + int(market_share * 5)),
            "benchmark": "$1B+ TAM, demonstrable market share, clear competitive moat",
            "current": f"${tam / 1e9:.1f}B TAM, {market_share:.1f}% share",
            "gap": "Define TAM" if tam == 0 else "Strong positioning" if market_share > 5 else "Build share",
        }

        # 7. Legal/IP Readiness (clean cap table, no material litigation, IP protected)
        clean_cap = target.get("clean_cap_table", False)
        ip_protected = target.get("ip_protected", False)
        no_litigation = target.get("no_material_litigation", True)
        legal_score = (35 if clean_cap else 0) + (35 if ip_protected else 0) + (30 if no_litigation else 0)
        gates["legal_ip"] = {
            "score": legal_score,
            "benchmark": "Clean cap table, IP protected, no material litigation",
            "current": f"{'Clean cap' if clean_cap else 'Cap issues'}, {'IP protected' if ip_protected else 'IP exposed'}, {'No litigation' if no_litigation else 'Litigation risk'}",
            "gap": "Address outstanding items" if legal_score < 70 else "Ready",
        }

        # 8. Investor Relations / Story (clear narrative, comparable public comps)
        has_ir_team = target.get("has_ir_capability", False)
        public_comps = target.get("public_comparable_count", 0)
        gates["investor_story"] = {
            "score": (40 if has_ir_team else 10) + min(60, public_comps * 15),
            "benchmark": "IR capability, 3+ public comps, clear equity story",
            "current": f"{'IR team' if has_ir_team else 'No IR'}, {public_comps} public comps",
            "gap": "Build IR capability" if not has_ir_team else "Ready",
        }

        # Overall IPO readiness
        scores = [g["score"] for g in gates.values()]
        overall = round(sum(scores) / len(scores))

        # Timeline estimate
        if overall >= 80:
            timeline = "6-12 months — IPO ready with minor preparations"
            verdict = "IPO_READY"
        elif overall >= 60:
            timeline = "12-24 months — significant preparation needed"
            verdict = "IPO_TRACK"
        elif overall >= 40:
            timeline = "24-36 months — major buildout required"
            verdict = "IPO_DEVELOPMENT"
        else:
            timeline = "36+ months — fundamental transformation needed"
            verdict = "NOT_READY"

        return {
            "overall_score": overall,
            "verdict": verdict,
            "timeline": timeline,
            "gates": gates,
            "passing_gates": sum(1 for g in gates.values() if g["score"] >= 70),
            "total_gates": len(gates),
            "critical_gaps": [name for name, g in gates.items() if g["score"] < 40],
        }


merlin = MerlinAgent()
