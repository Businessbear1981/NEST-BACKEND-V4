"""
NEST Hawkeye Routes — Institutional Placement & Sales Engine.
Pillar 4: Buyer matching, AI teasers, order book, allocation.
"""
from flask import Blueprint, jsonify, request
from services.auth import require_auth
from datetime import datetime
import threading
from services.auth import require_auth

hawkeye_bp = Blueprint("hawkeye", __name__)

_order_book = {}  # deal_id -> list of indications
_teasers = {}     # deal_id -> list of generated teasers
_lock = threading.Lock()

# Institutional buyer universe (seeded)
BUYER_UNIVERSE = [
    {"id": "inv_1", "name": "Redwood Family Office", "type": "family_office",
     "aum_usd": 450_000_000, "min_ticket_usd": 5_000_000, "max_ticket_usd": 50_000_000,
     "preferred_rating": "A", "preferred_sectors": ["6232", "6231", "5311"],
     "yield_floor_pct": 5.5, "relationship": "existing"},
    {"id": "inv_2", "name": "Cascadia Endowment Fund", "type": "endowment",
     "aum_usd": 1_200_000_000, "min_ticket_usd": 10_000_000, "max_ticket_usd": 100_000_000,
     "preferred_rating": "BBB+", "preferred_sectors": ["6232", "6231"],
     "yield_floor_pct": 6.0, "relationship": "existing"},
    {"id": "inv_3", "name": "Mariner Credit Partners", "type": "credit_fund",
     "aum_usd": 800_000_000, "min_ticket_usd": 15_000_000, "max_ticket_usd": 75_000_000,
     "preferred_rating": "BBB", "preferred_sectors": ["6232", "5311", "2361"],
     "yield_floor_pct": 7.0, "relationship": "new"},
    {"id": "inv_4", "name": "Pacific Northwest Pension", "type": "pension",
     "aum_usd": 3_500_000_000, "min_ticket_usd": 25_000_000, "max_ticket_usd": 200_000_000,
     "preferred_rating": "A", "preferred_sectors": ["6232", "6231"],
     "yield_floor_pct": 5.0, "relationship": "new"},
    {"id": "inv_5", "name": "Evergreen Insurance Co.", "type": "insurance",
     "aum_usd": 2_100_000_000, "min_ticket_usd": 20_000_000, "max_ticket_usd": 150_000_000,
     "preferred_rating": "A", "preferred_sectors": ["6232", "6231", "5311"],
     "yield_floor_pct": 4.8, "relationship": "existing"},
    {"id": "inv_6", "name": "Summit Capital Advisors", "type": "ria",
     "aum_usd": 280_000_000, "min_ticket_usd": 2_000_000, "max_ticket_usd": 25_000_000,
     "preferred_rating": "BBB+", "preferred_sectors": ["6232", "2361"],
     "yield_floor_pct": 6.5, "relationship": "new"},
]


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


@hawkeye_bp.route("/buyers", methods=["GET"])
def list_buyers():
    return _ok({"buyers": BUYER_UNIVERSE, "total": len(BUYER_UNIVERSE)})


@hawkeye_bp.route("/match", methods=["POST"])
def match_buyers():
    """Match institutional buyers to a deal based on sector, rating, yield, ticket size."""
    b = request.get_json() or {}
    deal_naics = b.get("naics", "6232")
    deal_rating = b.get("rating", "A")
    deal_coupon = b.get("coupon_pct", 6.5)
    deal_size = b.get("total_raise_usd", 100_000_000)
    a_tranche = b.get("a_tranche_usd", deal_size * 0.75)

    rating_order = ["A", "BBB+", "BBB", "BBB-", "BB+", "BB"]
    deal_rank = rating_order.index(deal_rating) if deal_rating in rating_order else 5

    matches = []
    for buyer in BUYER_UNIVERSE:
        score = 0
        rationale = []

        # Sector match (40 pts)
        if deal_naics in buyer["preferred_sectors"]:
            score += 40
            rationale.append("Sector match")

        # Yield clearance (25 pts)
        if deal_coupon >= buyer["yield_floor_pct"]:
            score += 25
            rationale.append(f"Yield {deal_coupon}% >= floor {buyer['yield_floor_pct']}%")

        # Rating comfort (20 pts)
        buyer_rank = rating_order.index(buyer["preferred_rating"]) if buyer["preferred_rating"] in rating_order else 5
        if deal_rank <= buyer_rank:
            score += 20
            rationale.append("Rating within comfort zone")

        # Ticket sizing (10 pts)
        if buyer["min_ticket_usd"] <= a_tranche <= buyer["max_ticket_usd"] * 3:
            score += 10
            rationale.append("Ticket size fit")

        # Relationship bonus (5 pts)
        if buyer["relationship"] == "existing":
            score += 5
            rationale.append("Existing relationship")

        suggested_ticket = min(
            buyer["max_ticket_usd"],
            max(buyer["min_ticket_usd"], int(a_tranche * 0.15))
        )

        matches.append({
            **buyer,
            "match_score": score,
            "rationale": rationale,
            "suggested_ticket_usd": suggested_ticket,
        })

    matches.sort(key=lambda m: m["match_score"], reverse=True)

    return _ok({
        "matches": matches,
        "total_matched": len([m for m in matches if m["match_score"] >= 40]),
        "potential_demand_usd": sum(m["suggested_ticket_usd"] for m in matches if m["match_score"] >= 40),
    })


@hawkeye_bp.route("/teaser", methods=["POST"])
def generate_teaser():
    """Generate AI-powered investor teaser for a deal."""
    b = request.get_json() or {}
    deal_id = b.get("dealId", "unknown")
    deal_name = b.get("dealName", "NEST Bond Offering")
    deal_size = b.get("totalRaise", 100_000_000)
    coupon = b.get("coupon", 6.5)
    rating = b.get("rating", "A")
    asset_type = b.get("assetType", "Senior Living CCRC")
    state = b.get("state", "FL")

    from services.ai_router import plugin_hub
    prompt = (
        f"Write a 200-word institutional investor teaser for:\n"
        f"Deal: {deal_name}\n"
        f"Asset: {asset_type} in {state}\n"
        f"Total raise: ${deal_size:,.0f}\n"
        f"Series A coupon: {coupon}%\n"
        f"Target rating: {rating}\n"
        f"Structure: NEST dual-tranche (A senior + B subordinate), Hylant surety wrap\n"
        f"Include: investment highlights, credit strengths, call protection, "
        f"and a clear call-to-action. Jimmy Lee tone — direct, decisive."
    )

    result = plugin_hub.route("investor_teaser", prompt)
    teaser = {
        "id": f"teaser_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "dealId": deal_id,
        "dealName": deal_name,
        "content": result.get("content", "") if result.get("success") else "Teaser generation unavailable",
        "tool_used": result.get("tool", "none"),
        "generatedAt": datetime.utcnow().isoformat(),
    }

    with _lock:
        _teasers.setdefault(deal_id, []).append(teaser)

    return _ok(teaser)


@hawkeye_bp.route("/order-book/<deal_id>", methods=["GET"])
def get_order_book(deal_id):
    with _lock:
        book = _order_book.get(deal_id, [])
    total = sum(o["amount_usd"] for o in book)
    return _ok({
        "dealId": deal_id,
        "orders": book,
        "total_indications_usd": total,
        "order_count": len(book),
    })


@hawkeye_bp.route("/order-book/<deal_id>/indicate", methods=["POST"])
def add_indication(deal_id):
    """Add investor indication to the order book."""
    b = request.get_json() or {}
    indication = {
        "id": f"ord_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "investorId": b.get("investorId"),
        "investorName": b.get("investorName", "Unknown"),
        "amount_usd": b.get("amount_usd", 0),
        "tranche": b.get("tranche", "A"),
        "yield_target_pct": b.get("yield_target_pct"),
        "status": "indicated",
        "indicatedAt": datetime.utcnow().isoformat(),
    }
    with _lock:
        _order_book.setdefault(deal_id, []).append(indication)
    return _ok(indication)


@hawkeye_bp.route("/order-book/<deal_id>/allocate", methods=["POST"])
def allocate(deal_id):
    """Run allocation — prioritize existing relationships, then largest indications."""
    b = request.get_json() or {}
    target_raise = b.get("target_raise_usd", 100_000_000)

    with _lock:
        book = _order_book.get(deal_id, [])

    # Sort: existing relationships first, then by amount descending
    existing_ids = {buyer["id"] for buyer in BUYER_UNIVERSE if buyer["relationship"] == "existing"}
    sorted_book = sorted(
        book,
        key=lambda o: (o["investorId"] in existing_ids, o["amount_usd"]),
        reverse=True,
    )

    allocated = 0
    allocations = []
    for order in sorted_book:
        if allocated >= target_raise:
            break
        alloc_amount = min(order["amount_usd"], target_raise - allocated)
        allocations.append({
            **order,
            "allocated_usd": alloc_amount,
            "status": "allocated",
        })
        allocated += alloc_amount

    return _ok({
        "dealId": deal_id,
        "target_raise_usd": target_raise,
        "total_allocated_usd": allocated,
        "remaining_usd": max(0, target_raise - allocated),
        "coverage_pct": round(allocated / target_raise * 100, 1) if target_raise else 0,
        "allocations": allocations,
    })


@hawkeye_bp.route("/teasers/<deal_id>", methods=["GET"])
def list_teasers(deal_id):
    with _lock:
        return _ok(_teasers.get(deal_id, []))
