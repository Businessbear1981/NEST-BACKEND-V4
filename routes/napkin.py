"""Back of the Napkin — quick spread calculator API."""

from datetime import datetime

from flask import Blueprint, jsonify, request

from services.napkin_engine import investor_re_napkin, owner_user_napkin

napkin_bp = Blueprint("napkin", __name__)


def _ok(data):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
    })


@napkin_bp.post("/owner-user")
def calc_owner_user():
    """Owner/User business banking spread. Eyes into the company."""
    body = request.get_json(silent=True) or {}
    return _ok(owner_user_napkin(body))


@napkin_bp.post("/investor-re")
def calc_investor_re():
    """Investor RE spread. Eyes into the property."""
    body = request.get_json(silent=True) or {}
    return _ok(investor_re_napkin(body))


@napkin_bp.get("/demo/owner-user")
def demo_owner_user():
    """Demo owner/user spread with sample data."""
    sample = {
        "cash": 850_000,
        "accounts_receivable": 1_200_000,
        "inventory": 600_000,
        "accounts_payable": 480_000,
        "current_assets": 2_800_000,
        "current_liabilities": 1_100_000,
        "total_assets": 12_400_000,
        "total_liabilities": 8_200_000,
        "total_equity": 4_200_000,
        "tangible_net_worth": 3_800_000,
        "revenue": 18_600_000,
        "cogs": 11_200_000,
        "ebitda": 3_400_000,
        "net_income": 1_800_000,
        "interest_expense": 680_000,
        "total_debt": 7_600_000,
        "funded_debt": 6_200_000,
        "depreciation": 420_000,
        "rent_expense": 360_000,
        "officers_comp": 480_000,
        "officers_debt_pi": 84_000,
        "tax_rate_pct": 21,
        "io_payments": 240_000,
        "pi_payments": 1_400_000,
    }
    return _ok(owner_user_napkin(sample))


@napkin_bp.get("/demo/investor-re")
def demo_investor_re():
    """Demo investor RE spread with sample data."""
    sample = {
        "noi": 7_800_000,
        "cap_rate_pct": 6.5,
        "requested_loan": 78_000_000,
        "coupon_pct": 6.5,
        "loan_term_years": 3,
        "amortization_years": 30,
        "occupancy_pct": 92,
        "replacement_cost": 145_000_000,
        "capex_reserve": 800_000,
        "deferred_maintenance": 1_200_000,
        "phase_i_clear": True,
        "tenants": [
            {"name": "Pacific Health Partners", "annual_rent": 2_016_000, "lease_expiry": "2029-06-30", "lease_type": "NNN", "pct_of_noi": 26},
            {"name": "TechVentures Inc", "annual_rent": 1_512_000, "lease_expiry": "2028-12-31", "lease_type": "NNN", "pct_of_noi": 19},
            {"name": "Meridian Capital", "annual_rent": 720_000, "lease_expiry": "2030-03-31", "lease_type": "NNN", "pct_of_noi": 9},
            {"name": "CoreLogic Analytics", "annual_rent": 972_000, "lease_expiry": "2028-09-30", "lease_type": "Modified Gross", "pct_of_noi": 12},
            {"name": "Vertex Legal Group", "annual_rent": 510_000, "lease_expiry": "2027-12-31", "lease_type": "NNN", "pct_of_noi": 7},
            {"name": "Cascade Engineering", "annual_rent": 1_080_000, "lease_expiry": "2029-03-31", "lease_type": "NNN", "pct_of_noi": 14},
            {"name": "Summit Advisory", "annual_rent": 540_000, "lease_expiry": "2028-06-30", "lease_type": "Gross", "pct_of_noi": 7},
            {"name": "Horizon Data Systems", "annual_rent": 450_000, "lease_expiry": "2027-09-30", "lease_type": "NNN", "pct_of_noi": 6},
        ],
    }
    return _ok(investor_re_napkin(sample))
