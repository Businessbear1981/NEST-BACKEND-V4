"""
NEST Roots Marketplace Service
Two-sided marketplace: investors browse deals, brokers submit deals.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict


# ── SEED OFFERINGS ────────────────────────────────────────────
# These are real deal structures. Not placeholder data.
_OFFERINGS = [
    {
        "id": "off_001",
        "name": "Life Star Pointe Loop",
        "asset_type": "Senior Living",
        "city": "Venice",
        "state": "FL",
        "structure": "Private Bond — Dual Tranche Series A/B",
        "description": "180-unit senior living facility. Venice, FL. 87% pre-leased commitments. Shovel ready Q3 2026. Hylant surety commitment in process.",
        "total_raise_usd": 147_600_000,
        "a_tranche_usd": 135_000_000,
        "b_tranche_usd": 12_600_000,
        "a_coupon_pct": 7.0,
        "b_coupon_pct": 11.0,
        "ltv_pct": 65.0,
        "dscr": 1.68,
        "grade_target": "BBB-",
        "surety_provider": "Hylant Insurance",
        "minimum_investment_usd": 250_000,
        "equity_available_pct": 15.0,
        "nest_arrangement_fee_pct": 2.25,
        "bond_ready": False,
        "bond_readiness_pct": 65,
        "bond_readiness_items": [
            {"item": "Phase I Environmental", "status": "complete"},
            {"item": "Appraisal", "status": "in_progress"},
            {"item": "GMP Contract", "status": "pending"},
            {"item": "Audited Financials", "status": "pending"},
            {"item": "Surety Commitment Letter", "status": "pending"},
        ],
        "investor_types": ["accredited", "qualified_purchaser", "family_office", "private_equity"],
        "status": "active",
        "created_at": "2026-01-15T00:00:00Z",
    },
    {
        "id": "off_002",
        "name": "Meridian Cove Senior Living",
        "asset_type": "Senior Living",
        "city": "Sarasota",
        "state": "FL",
        "structure": "Private Bond — Series A with Equity Co-Investment",
        "description": "95-unit memory care and assisted living. Sarasota, FL. Experienced operator. 3-year stabilized proforma at 92% occupancy.",
        "total_raise_usd": 77_900_000,
        "a_tranche_usd": 71_250_000,
        "b_tranche_usd": 6_650_000,
        "a_coupon_pct": 6.85,
        "b_coupon_pct": 10.5,
        "ltv_pct": 68.0,
        "dscr": 1.72,
        "grade_target": "BBB-",
        "surety_provider": "Hylant Insurance",
        "minimum_investment_usd": 150_000,
        "equity_available_pct": 20.0,
        "nest_arrangement_fee_pct": 2.0,
        "bond_ready": False,
        "bond_readiness_pct": 45,
        "bond_readiness_items": [
            {"item": "Phase I Environmental", "status": "complete"},
            {"item": "Appraisal", "status": "pending"},
            {"item": "GMP Contract", "status": "pending"},
            {"item": "Audited Financials", "status": "in_progress"},
            {"item": "Surety Commitment Letter", "status": "pending"},
        ],
        "investor_types": ["accredited", "family_office"],
        "status": "active",
        "created_at": "2026-02-01T00:00:00Z",
    },
]

_SUBMISSIONS: List[Dict] = []
_INTERESTS: List[Dict] = []


class RootsService:

    def get_offerings(self, filters: dict = None) -> list:
        offerings = [o for o in _OFFERINGS if o["status"] == "active"]
        if not filters:
            return offerings
        if filters.get("asset_type"):
            offerings = [o for o in offerings if o["asset_type"].lower() == filters["asset_type"].lower()]
        if filters.get("state"):
            offerings = [o for o in offerings if o["state"].upper() == filters["state"].upper()]
        if filters.get("bond_ready"):
            offerings = [o for o in offerings if o["bond_ready"]]
        if filters.get("max_min_investment"):
            offerings = [o for o in offerings
                        if o["minimum_investment_usd"] <= int(filters["max_min_investment"])]
        return offerings

    def get_offering(self, offering_id: str) -> Optional[dict]:
        return next((o for o in _OFFERINGS if o["id"] == offering_id), None)

    def get_bond_readiness(self, offering_id: str) -> dict:
        o = self.get_offering(offering_id)
        if not o:
            return {"error": "Not found"}
        items = o.get("bond_readiness_items", [])
        complete = sum(1 for i in items if i["status"] == "complete")
        in_progress = sum(1 for i in items if i["status"] == "in_progress")
        next_step = next((i["item"] for i in items if i["status"] == "pending"), None)
        return {
            "offering_id": offering_id,
            "bond_readiness_pct": o["bond_readiness_pct"],
            "bond_ready": o["bond_ready"],
            "items": items,
            "complete": complete,
            "in_progress": in_progress,
            "total": len(items),
            "next_step": next_step or "All items complete",
        }

    def register_interest(self, offering_id: str, investor: dict) -> dict:
        o = self.get_offering(offering_id)
        if not o:
            return {"success": False, "error": "Offering not found"}
        record = {
            "id": f"int_{uuid.uuid4().hex[:8]}",
            "offering_id": offering_id,
            "offering_name": o["name"],
            "investor_name": investor.get("name", ""),
            "investor_email": investor.get("email", ""),
            "investor_type": investor.get("type", "accredited"),
            "investment_amount_usd": investor.get("amount", 0),
            "accredited_certified": investor.get("accredited", False),
            "notes": investor.get("notes", ""),
            "status": "received",
            "created_at": datetime.utcnow().isoformat(),
        }
        _INTERESTS.append(record)
        return {
            "success": True,
            "interest_id": record["id"],
            "message": "Interest received. A NEST representative will contact you within 24 hours.",
        }

    def submit_deal(self, data: dict) -> dict:
        sub = {
            "id": f"sub_{uuid.uuid4().hex[:8]}",
            "contact_name": data.get("contact_name", ""),
            "contact_email": data.get("contact_email", ""),
            "contact_phone": data.get("contact_phone", ""),
            "project_name": data.get("project_name", ""),
            "asset_type": data.get("asset_type", ""),
            "city": data.get("city", ""),
            "state": data.get("state", ""),
            "loan_amount_usd": data.get("loan_amount_usd", 0),
            "description": data.get("description", ""),
            "broker_company": data.get("broker_company", ""),
            "relationship": data.get("relationship", ""),
            "current_stage": data.get("current_stage", ""),
            "nest_review_status": "pending",
            "submitted_at": datetime.utcnow().isoformat(),
        }
        _SUBMISSIONS.append(sub)
        return {
            "success": True,
            "submission_id": sub["id"],
            "message": "Deal submitted to NEST. We review all submissions within 48 hours.",
        }

    def get_all_submissions(self) -> list:
        return sorted(_SUBMISSIONS, key=lambda x: x["submitted_at"], reverse=True)

    def get_all_interests(self) -> list:
        return sorted(_INTERESTS, key=lambda x: x["created_at"], reverse=True)

    def update_submission_status(self, sub_id: str, status: str, notes: str = "") -> dict:
        sub = next((s for s in _SUBMISSIONS if s["id"] == sub_id), None)
        if not sub:
            return {"success": False, "error": "Not found"}
        sub["nest_review_status"] = status
        sub["admin_notes"] = notes
        sub["reviewed_at"] = datetime.utcnow().isoformat()
        return {"success": True, "submission": sub}


roots_service = RootsService()
