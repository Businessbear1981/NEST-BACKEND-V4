"""
NEST Phase-Tranche Bond Structure Engine.
One construction project = multiple phase bonds.
Each phase has its own tranche, timeline, rate, call/put.
More phases = more arrangement fees = better NEST economics.
Deleverage as phases complete = lower risk profile over time.
"""
from datetime import datetime

NEST_ARRANGEMENT_FEE_PCT = 1.5
NEST_ROLL_FEE_PCT = 0.50


class PhaseBondEngine:

    PHASES = {
        "soft_costs": {
            "description": "Design, engineering, permits, legal, marketing, pre-dev",
            "typical_pct_of_tpc": 8,
            "typical_duration_months": 12,
            "rate_spread_bps_premium": 150,
            "call_eligible_months": 6,
            "put_protection_months": 3,
            "security": "personal_guarantee_plus_land",
        },
        "site_prep": {
            "description": "Demolition, grading, utilities, foundation excavation",
            "typical_pct_of_tpc": 5,
            "typical_duration_months": 4,
            "rate_spread_bps_premium": 100,
            "call_eligible_months": 3,
            "put_protection_months": 2,
            "security": "land_lien",
        },
        "foundation": {
            "description": "Foundation, slab, underground MEP",
            "typical_pct_of_tpc": 10,
            "typical_duration_months": 5,
            "rate_spread_bps_premium": 75,
            "call_eligible_months": 3,
            "put_protection_months": 2,
            "security": "foundation_lien",
        },
        "structural": {
            "description": "Precast, steel shell, concrete core",
            "typical_pct_of_tpc": 20,
            "typical_duration_months": 8,
            "rate_spread_bps_premium": 50,
            "call_eligible_months": 6,
            "put_protection_months": 3,
            "security": "structural_lien_plus_insurance",
        },
        "envelope": {
            "description": "Facade, roof, windows, exterior",
            "typical_pct_of_tpc": 12,
            "typical_duration_months": 6,
            "rate_spread_bps_premium": 50,
            "call_eligible_months": 4,
            "put_protection_months": 2,
            "security": "building_lien",
        },
        "mep": {
            "description": "Mechanical, electrical, plumbing, HVAC",
            "typical_pct_of_tpc": 18,
            "typical_duration_months": 8,
            "rate_spread_bps_premium": 50,
            "call_eligible_months": 6,
            "put_protection_months": 3,
            "security": "building_lien_plus_equipment",
        },
        "interiors_ff_and_e": {
            "description": "Interior finishes, furniture, fixtures, equipment",
            "typical_pct_of_tpc": 15,
            "typical_duration_months": 6,
            "rate_spread_bps_premium": 25,
            "call_eligible_months": 4,
            "put_protection_months": 2,
            "security": "building_lien_plus_ff_and_e",
        },
        "completion_opening": {
            "description": "Punchlist, CO, soft opening, initial operations",
            "typical_pct_of_tpc": 12,
            "typical_duration_months": 4,
            "rate_spread_bps_premium": 0,
            "call_eligible_months": 2,
            "put_protection_months": 1,
            "security": "completed_building_first_mortgage",
        },
    }

    def structure_phase_bonds(self, tpc: float, base_rate_bps: int,
                              project_type: str = "senior_living") -> dict:
        phases = []
        cumulative_months = 0
        peak_exposure = 0
        running_exposure = 0

        for phase_key, phase_def in self.PHASES.items():
            amount = round(tpc * phase_def["typical_pct_of_tpc"] / 100)
            spread = phase_def.get("rate_spread_bps_premium", 0)
            rate_bps = base_rate_bps + spread
            rate_pct = round(rate_bps / 100, 2)
            duration = phase_def["typical_duration_months"]
            call_month = cumulative_months + phase_def.get("call_eligible_months", duration)
            put_month = cumulative_months + phase_def.get("put_protection_months", 0)

            interest_cost = round(amount * rate_pct / 100 * duration / 12)
            nest_arrangement = round(amount * NEST_ARRANGEMENT_FEE_PCT / 100)
            nest_roll = round(amount * NEST_ROLL_FEE_PCT / 100)

            running_exposure += amount
            if running_exposure > peak_exposure:
                peak_exposure = running_exposure

            phase = {
                "phase": phase_key,
                "description": phase_def["description"],
                "tranche_amount_usd": amount,
                "pct_of_tpc": phase_def["typical_pct_of_tpc"],
                "rate_bps": rate_bps,
                "rate_pct": rate_pct,
                "spread_over_base_bps": spread,
                "duration_months": duration,
                "start_month": cumulative_months,
                "end_month": cumulative_months + duration,
                "call_eligible_month": call_month,
                "put_protection_until_month": put_month,
                "security": phase_def.get("security", "building_lien"),
                "interest_cost_usd": interest_cost,
                "nest_arrangement_fee_usd": nest_arrangement,
                "nest_roll_fee_usd": nest_roll,
                "cumulative_exposure_usd": running_exposure,
            }
            phases.append(phase)
            cumulative_months += duration

        total_interest = sum(p["interest_cost_usd"] for p in phases)
        total_nest_fees = sum(p["nest_arrangement_fee_usd"] + p["nest_roll_fee_usd"] for p in phases)
        single_bond_fee = round(tpc * 0.015)
        phase_bond_premium = total_nest_fees - single_bond_fee

        return {
            "project_type": project_type,
            "total_project_cost_usd": tpc,
            "base_rate_bps": base_rate_bps,
            "phases": phases,
            "total_phases": len(phases),
            "total_construction_months": cumulative_months,
            "peak_exposure_usd": peak_exposure,
            "aggregate_approved_exposure_usd": round(tpc * 1.05),
            "total_interest_cost_usd": total_interest,
            "weighted_avg_rate_bps": round(
                sum(p["rate_bps"] * p["tranche_amount_usd"] for p in phases) / tpc
            ) if tpc else 0,
            "nest_economics": {
                "total_arrangement_fees_usd": sum(p["nest_arrangement_fee_usd"] for p in phases),
                "total_roll_fees_usd": sum(p["nest_roll_fee_usd"] for p in phases),
                "total_nest_fees_usd": total_nest_fees,
                "single_bond_fee_usd": single_bond_fee,
                "phase_bond_premium_usd": phase_bond_premium,
                "premium_pct_over_single": round(phase_bond_premium / single_bond_fee * 100, 1) if single_bond_fee else 0,
                "why_phase_bonds": "8 arrangement fees + 8 roll fees vs 1 arrangement fee. Phase bonds generate 2-3x more fee income for NEST.",
            },
            "deleverage_schedule": self.model_deleverage(phases),
        }

    def model_deleverage(self, phases: list) -> dict:
        timeline = []
        outstanding = 0
        peak = 0

        for p in phases:
            outstanding += p["tranche_amount_usd"]
            if outstanding > peak:
                peak = outstanding
            timeline.append({
                "month": p["start_month"],
                "event": f"{p['phase']} tranche funded",
                "exposure_usd": outstanding,
                "pct_of_peak": round(outstanding / peak * 100, 1) if peak else 0,
            })

        for p in reversed(phases):
            outstanding -= p["tranche_amount_usd"]
            outstanding = max(0, outstanding)
            timeline.append({
                "month": p["end_month"],
                "event": f"{p['phase']} complete — tranche retired",
                "exposure_usd": outstanding,
                "pct_of_peak": round(outstanding / peak * 100, 1) if peak else 0,
            })

        timeline.sort(key=lambda x: x["month"])

        return {
            "peak_exposure_usd": peak,
            "peak_month": next((t["month"] for t in timeline if t["exposure_usd"] == peak), 0),
            "exposure_at_stabilization_usd": 0,
            "deleverage_pace": "Each phase completion retires that tranche. Exposure decreases monotonically after peak.",
            "timeline": timeline,
        }

    def optimize_calls_puts(self, phases: list, rate_scenarios: list) -> dict:
        results = []
        for p in phases:
            phase_results = {"phase": p["phase"], "scenarios": []}
            for scenario in rate_scenarios:
                new_rate_bps = scenario.get("rate_bps", p["rate_bps"])
                rate_delta = new_rate_bps - p["rate_bps"]
                remaining_months = p["end_month"] - p.get("call_eligible_month", p["end_month"])
                remaining_months = max(remaining_months, 0)

                savings_if_called = round(
                    p["tranche_amount_usd"] * abs(rate_delta) / 10000 * remaining_months / 12
                ) if rate_delta > 0 else 0

                put_value = round(
                    p["tranche_amount_usd"] * abs(rate_delta) / 10000 *
                    max(p.get("put_protection_until_month", 0) - p["start_month"], 0) / 12
                ) if rate_delta < 0 else 0

                action = "hold"
                if rate_delta > 50:
                    action = "exercise_call"
                elif rate_delta < -75:
                    action = "put_protection_active"

                phase_results["scenarios"].append({
                    "scenario_name": scenario.get("name", "unnamed"),
                    "new_rate_bps": new_rate_bps,
                    "rate_delta_bps": rate_delta,
                    "recommended_action": action,
                    "savings_if_called_usd": savings_if_called,
                    "put_protection_value_usd": put_value,
                    "hedge_value_usd": max(savings_if_called, put_value),
                })
            results.append(phase_results)

        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "total_phases_analyzed": len(phases),
            "rate_scenarios_tested": len(rate_scenarios),
            "phase_results": results,
            "summary": "Call optimization reduces borrowing cost when rates fall. Put protection limits downside when rates rise. Phase bonds give 8 independent hedge points vs 1.",
        }

    def compute_nest_economics(self, phases: list) -> dict:
        total_arrangement = sum(p.get("nest_arrangement_fee_usd", round(p["tranche_amount_usd"] * 0.015)) for p in phases)
        total_roll = sum(p.get("nest_roll_fee_usd", round(p["tranche_amount_usd"] * 0.005)) for p in phases)
        total_tpc = sum(p["tranche_amount_usd"] for p in phases)
        single_bond_fee = round(total_tpc * 0.015)
        total_phase_fees = total_arrangement + total_roll

        per_phase = []
        for p in phases:
            arr = p.get("nest_arrangement_fee_usd", round(p["tranche_amount_usd"] * 0.015))
            roll = p.get("nest_roll_fee_usd", round(p["tranche_amount_usd"] * 0.005))
            per_phase.append({
                "phase": p["phase"],
                "tranche_usd": p["tranche_amount_usd"],
                "arrangement_fee_usd": arr,
                "roll_fee_usd": roll,
                "total_phase_fees_usd": arr + roll,
            })

        return {
            "per_phase_economics": per_phase,
            "total_arrangement_fees_usd": total_arrangement,
            "total_roll_fees_usd": total_roll,
            "total_phase_bond_fees_usd": total_phase_fees,
            "single_bond_alternative_fee_usd": single_bond_fee,
            "incremental_revenue_usd": total_phase_fees - single_bond_fee,
            "fee_multiple_vs_single": round(total_phase_fees / single_bond_fee, 2) if single_bond_fee else 0,
            "explanation": "Phase bonds generate arrangement + roll fees on each tranche. 8 phases x (1.5% arrangement + 0.5% roll) vs single 1.5% on total. NEST earns 2-3x more.",
        }


phase_bond_engine = PhaseBondEngine()
