"""
NEST Cross-Desk Workflow Engine — Deal lifecycle orchestration.

Implements the Operating Framework's cross-desk handoff specifications:
BD → Bond Desk → Credit → Rating → Structuring → Documents → Placement
→ Operations → Surveillance

Each transition has defined inputs, outputs, and gate conditions.
Bernard narrates at each transition point.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


WORKFLOW_STAGES = [
    {
        "id": "origination",
        "name": "Origination",
        "desk": "business_development",
        "description": "Deal sourced through Eagle Eye, inbound, or add-on pipeline",
        "gate_conditions": ["sponsor_identified", "preliminary_sizing_feasible", "principals_approved_intake"],
        "outputs": ["intake_package", "preliminary_sizing", "go_no_go_decision"],
        "next": "intake",
    },
    {
        "id": "intake",
        "name": "Bond Desk Intake",
        "desk": "bond_desk",
        "description": "Deal intake, document collection, readiness assessment",
        "gate_conditions": ["intake_docs_received", "readiness_score_above_60", "deal_type_confirmed"],
        "outputs": ["deal_record", "readiness_checklist", "use_case_assignment"],
        "next": "credit_underwriting",
    },
    {
        "id": "credit_underwriting",
        "name": "Credit Underwriting",
        "desk": "credit_underwriting",
        "description": "Credit analysis, memo production, credit policy compliance",
        "gate_conditions": ["credit_memo_complete", "universal_policy_passed", "exception_authority_if_needed"],
        "outputs": ["credit_memo", "credit_grade", "underwriting_flags", "exception_docs"],
        "next": "rating",
    },
    {
        "id": "rating",
        "name": "Rating Assessment",
        "desk": "rating",
        "description": "Mirror Agent rating prediction, agency selection, presentation prep",
        "gate_conditions": ["moodys_prediction_complete", "sp_prediction_complete", "rating_strategy_selected"],
        "outputs": ["predicted_moodys", "predicted_sp", "rating_strategy", "structural_levers"],
        "next": "structuring",
    },
    {
        "id": "structuring",
        "name": "Bond Structuring",
        "desk": "structuring",
        "description": "Bond structure design, amortization, covenants, reserves, pricing",
        "gate_conditions": ["structure_finalized", "covenant_package_complete", "pricing_range_set"],
        "outputs": ["bond_structure", "covenant_package", "reserve_sizing", "pricing_guidance", "sources_and_uses"],
        "next": "enhancement",
    },
    {
        "id": "enhancement",
        "name": "Credit Enhancement",
        "desk": "enhancement",
        "description": "Enhancement selection and procurement — insurance, LOC, surety, federal guarantee",
        "gate_conditions": ["enhancement_decision_made", "provider_engaged_if_applicable"],
        "outputs": ["enhancement_type", "enhanced_rating", "enhancement_cost", "provider_commitment"],
        "next": "documents",
    },
    {
        "id": "documents",
        "name": "Document Production",
        "desk": "documents",
        "description": "Indenture drafting, OS production, closing document assembly",
        "gate_conditions": ["indenture_draft_complete", "os_draft_complete", "bond_counsel_review_complete"],
        "outputs": ["draft_indenture", "draft_os", "closing_checklist", "document_package"],
        "next": "placement",
    },
    {
        "id": "placement",
        "name": "Bond Placement",
        "desk": "placement",
        "description": "Investor matching, marketing, order book, pricing, allocation",
        "gate_conditions": ["order_book_covered", "pricing_finalized", "allocation_approved"],
        "outputs": ["final_pricing", "investor_allocations", "bd_partner_confirmation"],
        "next": "closing",
    },
    {
        "id": "closing",
        "name": "Closing",
        "desk": "bond_desk",
        "description": "Closing execution, fund disbursement, bond delivery",
        "gate_conditions": ["all_closing_docs_executed", "funds_wired", "bonds_delivered"],
        "outputs": ["closing_transcript", "cusip_assigned", "trustee_notified"],
        "next": "operations",
    },
    {
        "id": "operations",
        "name": "Post-Closing Administration",
        "desk": "operations",
        "description": "Debt service admin, covenant monitoring, continuing disclosure, trustee coordination",
        "gate_conditions": ["administration_setup_complete", "trustee_onboarded", "first_payment_date_set"],
        "outputs": ["admin_schedule", "covenant_testing_calendar", "emma_filing_schedule"],
        "next": "surveillance",
    },
    {
        "id": "surveillance",
        "name": "Ongoing Surveillance",
        "desk": "surveillance",
        "description": "Portfolio monitoring, refunding identification, risk re-rating",
        "gate_conditions": [],
        "outputs": ["quarterly_surveillance_report", "refunding_opportunities", "risk_alerts"],
        "next": None,
    },
]


class WorkflowEngine:
    """Manages deal lifecycle across desks."""

    def __init__(self):
        self._deals: dict[str, dict] = {}

    def init_deal(self, deal_id: str, deal_type: str, source: str = "inbound") -> dict:
        """Initialize a deal in the workflow pipeline."""
        self._deals[deal_id] = {
            "deal_id": deal_id,
            "deal_type": deal_type,
            "source": source,
            "current_stage": "origination",
            "stage_history": [{"stage": "origination", "entered_at": datetime.utcnow().isoformat(), "status": "active"}],
            "gates_passed": [],
            "outputs": {},
            "created_at": datetime.utcnow().isoformat(),
        }
        return self._deals[deal_id]

    def get_deal_workflow(self, deal_id: str) -> dict | None:
        """Get current workflow state for a deal."""
        return self._deals.get(deal_id)

    def get_current_stage(self, deal_id: str) -> dict | None:
        """Get the current stage definition for a deal."""
        deal = self._deals.get(deal_id)
        if not deal:
            return None
        stage_id = deal["current_stage"]
        return next((s for s in WORKFLOW_STAGES if s["id"] == stage_id), None)

    def pass_gate(self, deal_id: str, gate_condition: str) -> dict:
        """Mark a gate condition as passed for the current stage."""
        deal = self._deals.get(deal_id)
        if not deal:
            return {"error": "Deal not found"}
        if gate_condition not in deal["gates_passed"]:
            deal["gates_passed"].append(gate_condition)
        stage = self.get_current_stage(deal_id)
        all_gates = stage["gate_conditions"] if stage else []
        all_passed = all(g in deal["gates_passed"] for g in all_gates)
        return {
            "deal_id": deal_id,
            "stage": deal["current_stage"],
            "gate_passed": gate_condition,
            "all_gates_passed": all_passed,
            "remaining_gates": [g for g in all_gates if g not in deal["gates_passed"]],
            "can_advance": all_passed,
        }

    def advance_stage(self, deal_id: str) -> dict:
        """Advance deal to next stage if all gates passed."""
        deal = self._deals.get(deal_id)
        if not deal:
            return {"error": "Deal not found"}
        current = self.get_current_stage(deal_id)
        if not current:
            return {"error": "Invalid stage"}
        all_gates = current["gate_conditions"]
        remaining = [g for g in all_gates if g not in deal["gates_passed"]]
        if remaining:
            return {"error": "Gates not passed", "remaining": remaining}
        next_stage = current["next"]
        if not next_stage:
            return {"error": "Deal at final stage (surveillance)"}

        deal["stage_history"].append({
            "stage": deal["current_stage"],
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed",
        })
        deal["current_stage"] = next_stage
        deal["gates_passed"] = []
        deal["stage_history"].append({
            "stage": next_stage,
            "entered_at": datetime.utcnow().isoformat(),
            "status": "active",
        })
        return {
            "deal_id": deal_id,
            "previous_stage": current["id"],
            "current_stage": next_stage,
            "desk": next((s["desk"] for s in WORKFLOW_STAGES if s["id"] == next_stage), None),
            "gate_conditions": next((s["gate_conditions"] for s in WORKFLOW_STAGES if s["id"] == next_stage), []),
        }

    def get_pipeline(self) -> list[dict]:
        """Get all deals with their current stage."""
        return [
            {
                "deal_id": d["deal_id"],
                "deal_type": d["deal_type"],
                "current_stage": d["current_stage"],
                "desk": next((s["desk"] for s in WORKFLOW_STAGES if s["id"] == d["current_stage"]), None),
                "created_at": d["created_at"],
            }
            for d in self._deals.values()
        ]

    def get_stages(self) -> list[dict]:
        """Return all workflow stages."""
        return WORKFLOW_STAGES
