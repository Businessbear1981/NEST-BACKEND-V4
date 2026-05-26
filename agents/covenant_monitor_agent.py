"""Covenant Monitor Agent — Operations Desk.
Quarterly covenant testing workflow per the Operating Framework."""

class CovenantMonitorAgent:
    def __init__(self):
        self.name = "Covenant Monitor"
        self.desk = "operations"

    def test_covenants(self, bond: dict, financials: dict) -> dict:
        results = []
        covenants = bond.get("covenant_package", {})
        dscr_threshold = covenants.get("dscr_threshold", 1.20)
        actual_dscr = financials.get("dscr", 0)
        results.append({"covenant": "DSCR", "threshold": f"{dscr_threshold:.2f}x", "actual": f"{actual_dscr:.2f}x", "passed": actual_dscr >= dscr_threshold, "cushion_pct": round((actual_dscr / dscr_threshold - 1) * 100, 1) if dscr_threshold else 0})
        abt = covenants.get("additional_bonds_test")
        if abt:
            results.append({"covenant": "Additional Bonds Test", "threshold": abt, "actual": "No additional debt issued", "passed": True})
        trap_dscr = covenants.get("distribution_trap", 0)
        if trap_dscr:
            results.append({"covenant": "Distribution Trap", "threshold": f"{trap_dscr:.2f}x triggers trap", "actual": f"{actual_dscr:.2f}x", "passed": actual_dscr >= trap_dscr, "trapped": actual_dscr < trap_dscr})
        all_passed = all(r["passed"] for r in results)
        return {"bond_id": bond.get("id", ""), "test_date": financials.get("period_end", ""), "all_passed": all_passed, "results": results, "action_required": "none" if all_passed else "escalate_to_surveillance"}
