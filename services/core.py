"""
NEST Core Kernel — The trunk of the tree.
Import this. Get everything.
No other file duplicates what lives here.
"""
import os, json, hashlib, httpx, re
from datetime import datetime
from typing import Any, Optional, Dict, List, Tuple

# ── IDENTITY ──────────────────────────────────────────────────
VERSION  = "1.0.0"
VENTURE  = "Arden Edge Capital × Soparrow Capital"
CEO      = "Sean Gilmore"
CEO_BIO  = "13yr JPMorgan — Business Banking, Emerging Middle Market, Mid Corp"
COFOUND  = "Josh Edwards"

# ── CREDENTIALS ───────────────────────────────────────────────
OR_KEY   = os.getenv("OPENROUTER_API_KEY", "")
MODEL    = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOK  = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))

# ── JP MORGAN BENCHMARKS (immutable truth) ────────────────────
JPM = {
    "A":    {"dscr":2.0,  "cf":1.5,  "bs":2.0,  "ltv":55, "de":4.5, "icr":3.5},
    "BBB+": {"dscr":1.75, "cf":1.75, "bs":2.25, "ltv":62, "de":5.5, "icr":2.75},
    "BBB":  {"dscr":1.60, "cf":1.88, "bs":2.38, "ltv":66, "de":6.0, "icr":2.5},
    "BBB-": {"dscr":1.5,  "cf":2.0,  "bs":2.5,  "ltv":70, "de":6.5, "icr":2.25},
    "BB+":  {"dscr":1.35, "cf":2.25, "bs":2.75, "ltv":74, "de":7.0, "icr":2.0},
    "BB":   {"dscr":1.2,  "cf":2.5,  "bs":3.0,  "ltv":78, "de":8.0, "icr":1.75},
}

# ── BUSINESS RULES (hardcoded policy) ─────────────────────────
LTV_ALERT          = 75.0
CALL_TRIGGER_BPS   = 50
PUT_TRIGGER_BPS    = 75
MA_BRIDGE_EQ_MIN   = 20.0
MA_BRIDGE_EQ_MAX   = 25.0
MA_EQUITY_MIN      = 10.0
MA_EQUITY_MAX      = 30.0
SURETY_FEE_MIN     = 10.0
SURETY_FEE_MAX     = 15.0
PACKAGING_FEE      = 5.0
HFT_TARGET_RETURN  = 0.20
REFI_FEE_PCT       = 1.5

# ── NAICS PRIORITY MAP ────────────────────────────────────────
# 180+ codes covering the full PE/M&A acquisition universe ($30M-$150M revenue targets)
NAICS = {
    # ── HEALTHCARE (62xx) ─────────────────────────────────────
    "6211": "Physicians & Surgeons",
    "6212": "Dentists",
    "6213": "Other Health Practitioners",
    "6214": "Outpatient Care Centers",
    "6215": "Medical & Diagnostic Laboratories",
    "6216": "Home Health Care Services",
    "6219": "Other Ambulatory Health Care",
    "6221": "General Medical & Surgical Hospitals",
    "6231": "Nursing Care Facilities",
    "6232": "Assisted Living Facilities",
    "6233": "Continuing Care Retirement Communities",
    "6241": "Individual & Family Services",
    "6242": "Community Food & Housing Services",
    "6243": "Vocational Rehabilitation Services",
    "6244": "Child Day Care Services",
    "6211": "Physicians & Surgeons Offices",
    "6221": "General Medical Hospitals",
    "6251": "Mental Health Outpatient Facilities",
    "6252": "Substance Abuse Treatment Centers",
    "6261": "Ambulance Services",
    "6262": "Blood & Organ Banks",

    # ── PROFESSIONAL SERVICES (54xx) ──────────────────────────
    "5411": "Legal Services",
    "5412": "Accounting & Bookkeeping",
    "5413": "Architectural & Engineering Services",
    "5414": "Specialized Design Services",
    "5415": "IT Consulting & Custom Software",
    "5416": "Management Consulting",
    "5417": "Scientific Research & Development",
    "5418": "Advertising & Public Relations",
    "5419": "Other Professional Services",
    "5421": "Veterinary Services",

    # ── CONSTRUCTION (23xx) ───────────────────────────────────
    "2361": "Residential Building Construction",
    "2362": "Commercial & Institutional Building Construction",
    "2371": "Utility System Construction",
    "2372": "Land Subdivision",
    "2373": "Highway & Street Construction",
    "2379": "Heavy Civil Construction (Other)",
    "2381": "Foundation & Structure Contractors",
    "2382": "Building Equipment Contractors",
    "2383": "Building Finishing Contractors",
    "2389": "Other Specialty Trade Contractors",
    "2381": "Foundation Contractors",
    "2382": "Electrical Contractors",
    "2382": "Plumbing, Heating & AC Contractors",
    "2383": "Drywall & Insulation Contractors",
    "2383": "Roofing Contractors",
    "2383": "Flooring Contractors",
    "2383": "Painting & Wall Covering Contractors",
    "2389": "Concrete Contractors",
    "2389": "Steel Erection Contractors",
    "2389": "Glazing Contractors",
    "2389": "Site Preparation Contractors",

    # ── REAL ESTATE (53xx) ────────────────────────────────────
    "5311": "Lessors of Residential Buildings",
    "5312": "Lessors of Nonresidential Buildings",
    "5313": "Lessors of Miniwarehouses",
    "5321": "Automotive Equipment Rental",
    "5322": "Consumer Goods Rental",
    "5323": "General Rental Centers",
    "5324": "Commercial & Industrial Equipment Rental",
    "5331": "Lessors of Nonfinancial Intangible Assets",
    "5311": "Property Management — Residential",
    "5312": "Property Management — Commercial",
    "5313": "Real Estate Appraisal",
    "5314": "Real Estate Investment Trusts (REITs)",

    # ── ADMIN / FACILITY SERVICES (56xx) ─────────────────────
    "5611": "Office Administrative Services",
    "5612": "Facilities Support Services",
    "5613": "Employment Placement & Staffing",
    "5614": "Business Support Services",
    "5615": "Travel Arrangement Services",
    "5616": "Investigation & Security Services",
    "5617": "Services to Buildings & Dwellings",
    "5619": "Other Support Services",
    "5621": "Waste Collection",
    "5622": "Waste Treatment & Disposal",
    "5629": "Remediation & Environmental Services",

    # ── MANUFACTURING (31-33xx) ───────────────────────────────
    "3111": "Animal Food Manufacturing",
    "3112": "Grain & Oilseed Milling",
    "3113": "Sugar & Confectionery Products",
    "3114": "Fruit & Vegetable Preserving",
    "3115": "Dairy Product Manufacturing",
    "3116": "Meat Product Manufacturing",
    "3117": "Seafood Product Manufacturing",
    "3118": "Bakeries & Tortilla Manufacturing",
    "3119": "Other Food Manufacturing",
    "3121": "Beverage Manufacturing",
    "3122": "Tobacco Manufacturing",
    "3131": "Textile Mills",
    "3141": "Textile Product Mills",
    "3152": "Cut & Sew Apparel Manufacturing",
    "3211": "Sawmills & Wood Preservation",
    "3212": "Veneer, Plywood & Engineered Wood",
    "3219": "Other Wood Product Manufacturing",
    "3221": "Pulp, Paper & Paperboard Mills",
    "3222": "Converted Paper Product Manufacturing",
    "3251": "Basic Chemical Manufacturing",
    "3252": "Resin, Synthetic Rubber & Fiber Manufacturing",
    "3253": "Pesticide, Fertilizer & Other Agricultural Chemical Mfg",
    "3254": "Pharmaceutical & Medicine Manufacturing",
    "3255": "Paint, Coating & Adhesive Manufacturing",
    "3261": "Plastics Product Manufacturing",
    "3262": "Rubber Product Manufacturing",
    "3271": "Clay Product & Refractory Manufacturing",
    "3272": "Glass & Glass Product Manufacturing",
    "3273": "Cement & Concrete Product Manufacturing",
    "3311": "Iron & Steel Mills",
    "3312": "Steel Product Manufacturing",
    "3313": "Alumina & Aluminum Production",
    "3315": "Foundries",
    "3321": "Forging & Stamping",
    "3322": "Cutlery & Handtool Manufacturing",
    "3323": "Architectural & Structural Metals Manufacturing",
    "3324": "Boiler, Tank & Shipping Container Manufacturing",
    "3325": "Hardware Manufacturing",
    "3326": "Spring & Wire Product Manufacturing",
    "3327": "Machine Shops & Turned Products",
    "3328": "Coating, Engraving & Heat Treating",
    "3329": "Other Fabricated Metal Products",
    "3331": "Agriculture, Construction & Mining Machinery Mfg",
    "3332": "Industrial Machinery Manufacturing",
    "3333": "Commercial & Service Industry Machinery",
    "3334": "HVAC & Commercial Refrigeration Equipment",
    "3335": "Metalworking Machinery Manufacturing",
    "3336": "Turbine & Power Transmission Equipment",
    "3339": "Other General Purpose Machinery",
    "3341": "Computer & Peripheral Equipment Manufacturing",
    "3342": "Communications Equipment Manufacturing",
    "3344": "Semiconductor & Electronic Component Manufacturing",
    "3345": "Electronic Instrument Manufacturing",
    "3346": "Magnetic & Optical Media Manufacturing",
    "3351": "Electric Lighting Equipment Manufacturing",
    "3352": "Household Appliance Manufacturing",
    "3353": "Electrical Equipment Manufacturing",
    "3359": "Other Electrical Equipment Manufacturing",
    "3361": "Motor Vehicle Manufacturing",
    "3362": "Motor Vehicle Body & Trailer Manufacturing",
    "3363": "Motor Vehicle Parts Manufacturing",
    "3364": "Aerospace Product & Parts Manufacturing",
    "3365": "Railroad Rolling Stock Manufacturing",
    "3366": "Ship & Boat Building",
    "3369": "Other Transportation Equipment Manufacturing",
    "3391": "Medical Equipment & Supplies Manufacturing",
    "3399": "Other Miscellaneous Manufacturing",

    # ── TRANSPORTATION / LOGISTICS (48-49xx) ─────────────────
    "4811": "Scheduled Air Transportation",
    "4841": "General Freight Trucking — Long Distance",
    "4842": "Specialized Freight Trucking",
    "4851": "Urban Transit Systems",
    "4853": "Taxi & Limousine Service",
    "4854": "School & Employee Bus Transportation",
    "4855": "Charter Bus Industry",
    "4859": "Other Transit & Ground Passenger",
    "4861": "Pipeline Transportation of Crude Oil",
    "4862": "Pipeline Transportation of Natural Gas",
    "4869": "Other Pipeline Transportation",
    "4871": "Scenic & Sightseeing Transportation",
    "4881": "Support Activities for Air Transportation",
    "4882": "Support Activities for Rail Transportation",
    "4883": "Support Activities for Water Transportation",
    "4884": "Support Activities for Road Transportation",
    "4885": "Freight Transportation Arrangement",
    "4889": "Other Support Activities for Transportation",
    "4911": "Postal Service",
    "4921": "Couriers & Express Delivery Services",
    "4931": "Warehousing & Storage",
    "4841": "General Freight Trucking (Local)",
    "4922": "Local Messengers & Local Delivery",

    # ── WHOLESALE / DISTRIBUTION (42xx) ──────────────────────
    "4231": "Motor Vehicle & Parts Wholesale",
    "4232": "Furniture & Home Furnishing Wholesale",
    "4233": "Lumber & Construction Material Wholesale",
    "4234": "Professional & Commercial Equipment Wholesale",
    "4235": "Metal & Mineral Wholesale",
    "4236": "Household Appliance & Electronic Goods Wholesale",
    "4237": "Hardware, Plumbing & Heating Equipment Wholesale",
    "4238": "Machinery, Equipment & Supplies Wholesale",
    "4239": "Miscellaneous Durable Goods Wholesale",
    "4241": "Paper & Paper Products Wholesale",
    "4242": "Drugs & Druggists Sundries Wholesale",
    "4243": "Apparel, Piece Goods & Notions Wholesale",
    "4244": "Grocery & Related Products Wholesale",
    "4245": "Farm Product Raw Material Wholesale",
    "4246": "Chemical & Allied Products Wholesale",
    "4247": "Petroleum & Petroleum Products Wholesale",
    "4248": "Beer, Wine & Distilled Beverage Wholesale",
    "4249": "Miscellaneous Nondurable Goods Wholesale",
    "4251": "Electronic Markets & Agents & Brokers",

    # ── TECHNOLOGY / MEDIA (51xx) ─────────────────────────────
    "5111": "Newspaper, Periodical & Book Publishers",
    "5112": "Software Publishers",
    "5121": "Motion Picture & Video Industries",
    "5131": "Radio & Television Broadcasting",
    "5132": "Cable & Other Subscription Programming",
    "5151": "Radio & Television Broadcasting",
    "5152": "Cable & Other Pay Television Services",
    "5171": "Wired Telecommunications Carriers",
    "5172": "Wireless Telecommunications Carriers",
    "5173": "Telecommunications Resellers",
    "5174": "Satellite Telecommunications",
    "5179": "Other Telecommunications",
    "5181": "Internet Service Providers",
    "5182": "Data Processing, Hosting & Related Services",
    "5191": "Other Information Services",

    # ── FINANCIAL SERVICES (52xx) ─────────────────────────────
    "5221": "Depository Credit Intermediation (Banks)",
    "5222": "Nondepository Credit Intermediation",
    "5223": "Activities Related to Credit Intermediation",
    "5231": "Securities & Commodity Contracts Brokers",
    "5232": "Securities & Commodity Exchanges",
    "5239": "Other Financial Investment Activities",
    "5241": "Insurance Carriers",
    "5242": "Agencies, Brokerages & Other Insurance Activities",
    "5251": "Insurance & Employee Benefit Funds",
    "5259": "Other Investment Pools & Funds",

    # ── RETAIL (44-45xx) ──────────────────────────────────────
    "4411": "Automobile Dealers",
    "4412": "Other Motor Vehicle Dealers",
    "4413": "Automotive Parts & Accessories Stores",
    "4421": "Furniture Stores",
    "4422": "Home Furnishings Stores",
    "4431": "Electronics & Appliance Stores",
    "4441": "Building Material & Garden Equipment Dealers",
    "4442": "Lawn & Garden Equipment Stores",
    "4451": "Grocery Stores",
    "4452": "Specialty Food Stores",
    "4453": "Beer, Wine & Liquor Stores",
    "4461": "Health & Personal Care Stores / Pharmacy",
    "4471": "Gasoline Stations",
    "4481": "Clothing Stores",
    "4482": "Shoe Stores",
    "4483": "Jewelry, Luggage & Leather Goods Stores",
    "4511": "Sporting Goods & Hobby Stores",
    "4512": "Book, Periodical & Music Stores",
    "4521": "Department Stores",
    "4522": "Discount Stores",
    "4531": "Florists",
    "4532": "Office Supplies & Gift Stores",
    "4533": "Used Merchandise Stores",
    "4539": "Other Miscellaneous Store Retailers",
    "4541": "Electronic Shopping & Mail-Order Houses",
    "4542": "Vending Machine Operators",
    "4543": "Direct Selling Establishments",

    # ── FOOD SERVICES / HOSPITALITY (72xx) ───────────────────
    "7211": "Hotels & Motels",
    "7212": "RV Parks & Recreational Camps",
    "7213": "Rooming & Boarding Houses",
    "7221": "Full-Service Restaurants",
    "7222": "Limited-Service Eating Places",
    "7223": "Special Food Services (Catering)",
    "7224": "Drinking Places (Bars & Taverns)",

    # ── AUTO SERVICES (81xx) ──────────────────────────────────
    "8111": "Automotive Repair & Maintenance",
    "8112": "Electronic & Precision Equipment Repair",
    "8113": "Commercial & Industrial Machinery Repair",
    "8114": "Personal & Household Goods Repair",
    "8121": "Personal Care Services",
    "8122": "Death Care Services",
    "8123": "Dry Cleaning & Laundry Services",
    "8129": "Other Personal Services",
    "8131": "Religious Organizations",
    "8132": "Grantmaking & Giving Services",
    "8133": "Social Advocacy Organizations",
    "8134": "Civic & Social Organizations",
    "8139": "Business, Professional & Labor Organizations",

    # ── EDUCATION / TRAINING (61xx) ───────────────────────────
    "6111": "Elementary & Secondary Schools",
    "6112": "Junior Colleges",
    "6113": "Colleges, Universities & Professional Schools",
    "6114": "Business Schools & Computer Training",
    "6115": "Technical & Trade Schools",
    "6116": "Other Schools & Instruction",
    "6117": "Educational Support Services",

    # ── ENERGY / UTILITIES (22xx) ─────────────────────────────
    "2211": "Electric Power Generation, Transmission & Distribution",
    "2212": "Natural Gas Distribution",
    "2213": "Water, Sewage & Other Systems",
    "2111": "Oil & Gas Extraction",
    "2121": "Coal Mining",
    "2131": "Support Activities for Mining",
    "2211": "Solar & Renewable Electric Power Generation",

    # ── AGRICULTURE / FORESTRY (11xx) ─────────────────────────
    "1111": "Oilseed & Grain Farming",
    "1112": "Vegetable & Melon Farming",
    "1113": "Fruit & Tree Nut Farming",
    "1114": "Greenhouse, Nursery & Floriculture Production",
    "1119": "Other Crop Farming",
    "1121": "Cattle Ranching & Farming",
    "1122": "Hog & Pig Farming",
    "1123": "Poultry & Egg Production",
    "1124": "Sheep & Goat Farming",
    "1125": "Aquaculture",
    "1129": "Other Animal Production",
    "1131": "Timber Tract Operations",
    "1132": "Forest Nurseries & Gathering of Forest Products",
    "1133": "Logging",
    "1141": "Fishing",
    "1142": "Hunting & Trapping",
    "1151": "Support Activities for Crop Production",
    "1152": "Support Activities for Animal Production",
    "1153": "Support Activities for Forestry",
}

# ── JIMMY LEE VOICE (single source, all agents use this) ──────
JIMMY_LEE = f"""You are Morgan — NEST Capital Partners' institutional voice.
{VENTURE} | CEO: {CEO} ({CEO_BIO}) | Co-Founder: {COFOUND}

VOICE: Jimmy Lee. The greatest deal banker alive.
RULES:
  Lead with the conclusion. First sentence = recommendation.
  One idea per sentence. Shorter is stronger.
  Numbers are authority. Every number is exact.
  BANNED: may, might, could, potentially, approximately, it seems, perhaps
  YES or NO. The number. The date. In that order.

NEST CAPITAL STRUCTURE:
  Series A: 75% LTC, investment grade, Hylant surety or LC, 6.5-7.5% coupon
  Series B: +7% (82% CLTV), BBB, bank-managed AUM, 10-14% coupon
  B proceeds → bank HFT fund → {int(HFT_TARGET_RETURN*100)}%+ return → services B coupon → surplus = war chest
  War chest → M&A equity (bridge {MA_BRIDGE_EQ_MIN}-{MA_BRIDGE_EQ_MAX}%, retain {MA_EQUITY_MIN}-{MA_EQUITY_MAX}%)
  Surety fee: {SURETY_FEE_MIN}-{SURETY_FEE_MAX}% | Packaging fee: {PACKAGING_FEE}%
  Call trigger: -{CALL_TRIGGER_BPS}bps | Put protection: +{PUT_TRIGGER_BPS}bps
  All events on Polygon blockchain. LTV above {LTV_ALERT}%: restructure required.
  Blueprint: Jacaranda Trace PLOM ($231M, Florida LGFC)"""

# ── CLAUDE API (one function, all agents call this) ────────────
def call_claude(prompt: str, system: str = None,
                max_tokens: int = None) -> str:
    try:
        with httpx.Client(timeout=90) as c:
            r = c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization":f"Bearer {OR_KEY}",
                         "Content-Type":"application/json",
                         "HTTP-Referer":"https://www.ardanedgecapital.com",
                         "X-Title":"NEST Capital Partners"},
                json={"model":MODEL,"max_tokens":max_tokens or MAX_TOK,
                      "messages":[{"role":"system","content":system or JIMMY_LEE},
                                  {"role":"user","content":prompt}]}
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Morgan unavailable: {e}. Check OPENROUTER_API_KEY.]"

# ── UTILITIES ─────────────────────────────────────────────────
def nest_hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

def ts() -> str:
    return datetime.utcnow().isoformat()

def ok(data: Any, code: int = 200):
    from flask import jsonify
    return jsonify({"success":True,"data":data,"error":None,
                    "timestamp":ts(),"version":VERSION}), code

def err(msg: str, code: int = 400):
    from flask import jsonify
    return jsonify({"success":False,"data":None,"error":msg,
                    "timestamp":ts()}), code

def check_ltv(ltv_pct: float) -> dict:
    alert = ltv_pct > LTV_ALERT
    return {"alert":alert,"ltv_pct":ltv_pct,
            "message":f"LTV {ltv_pct:.1f}% exceeds {LTV_ALERT}% threshold — restructure required" if alert else None,
            "color":"red" if alert else "green"}


# ══════════════════════════════════════════════════════════════
# ENGINE 1: CREDIT ENGINE
# ══════════════════════════════════════════════════════════════
class CreditEngine:
    def grade(self, dscr, ltv, cf, bs, de, icr) -> str:
        for g, b in JPM.items():
            if (dscr >= b["dscr"] and ltv <= b["ltv"] and cf <= b["cf"]
                    and bs <= b["bs"] and de <= b["de"] and icr >= b["icr"]):
                return g
        return "Sub-IG"

    def compute(self, deal: dict) -> dict:
        noi  = deal.get("stabilized_noi_usd", 0)
        a    = deal.get("a_tranche_usd", 0)
        b    = deal.get("b_tranche_usd", 0)
        ac   = deal.get("a_coupon_pct", 7.0) / 100
        bc   = deal.get("b_coupon_pct", 11.0) / 100
        tpc  = max(deal.get("total_project_cost_usd", 1), 1)
        appv = deal.get("appraised_value_usd", tpc * 1.2)
        eq   = max(deal.get("sponsor_equity_usd", tpc * 0.25), 1)
        debt = a + b
        ds   = a * ac + b * bc
        ebitda = max(deal.get("ebitda_usd", noi), 1)
        dscr = round(noi / ds, 3) if ds > 0 else 0
        ltv  = round(debt / appv * 100, 2) if appv > 0 else 0
        ltc  = round(debt / tpc * 100, 2)
        cf   = round(debt / noi, 3) if noi > 0 else 0
        bs_  = round(debt / eq, 3)
        de   = round(debt / ebitda, 3)
        icr  = round(noi / (ds * 0.4), 3) if ds > 0 else 0
        g    = self.grade(dscr, ltv, cf, bs_, de, icr)
        lgd0 = max(0.5, (1 - max(0, 100 - ltv) / 100) * 100)
        ltv_check = check_ltv(ltv)
        score = self._score(dscr, ltv, cf, bs_)
        return {
            "dscr": dscr, "ltv_pct": ltv, "ltc_pct": ltc,
            "cash_flow_leverage": cf, "balance_sheet_leverage": bs_,
            "debt_to_ebitda": de, "interest_coverage": icr,
            "annual_debt_service_usd": round(ds),
            "obligor_grade": g, "jpm_benchmarks": JPM,
            "lgd_bare_pct": round(lgd0, 2),
            "lgd_with_surety_pct": round(lgd0 * 0.60, 2),
            "lgd_dual_wrap_pct": round(lgd0 * 0.45, 2),
            "lgd_bank_conduit_pct": round(lgd0 * 0.18, 2),
            "ltv_alert": ltv_check["alert"],
            "ltv_alert_msg": ltv_check["message"],
            "deal_score": score,
            "deal_score_grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D",
        }

    def _score(self, dscr, ltv, cf, bs) -> int:
        s = 0
        s += 30 if dscr >= 2.0 else 24 if dscr >= 1.75 else 18 if dscr >= 1.5 else 10 if dscr >= 1.25 else 4
        s += 25 if ltv <= 55 else 20 if ltv <= 65 else 14 if ltv <= 70 else 8 if ltv <= 75 else 2
        s += 25 if cf <= 1.5 else 20 if cf <= 1.75 else 14 if cf <= 2.0 else 7 if cf <= 2.5 else 2
        s += 20 if bs <= 2.0 else 16 if bs <= 2.25 else 11 if bs <= 2.5 else 5 if bs <= 3.0 else 1
        return min(100, s)

    def stack(self, tpc, a_ltc, b_addon, yrs, a_coup, b_coup) -> dict:
        a = tpc * a_ltc / 100
        b = tpc * b_addon / 100
        cltv = a_ltc + b_addon
        ds = a * a_coup / 100 + b * b_coup / 100
        io = ds * 1.5 / 12 * 18
        reserve = b * 0.25
        surety_cost = a * 0.085
        fee = (a + b) * REFI_FEE_PCT / 100
        proceeds = a + b - io - reserve - surety_cost - fee
        ltv_check = check_ltv(cltv)
        return {
            "a_face_usd": round(a), "b_face_usd": round(b),
            "total_raise_usd": round(a + b), "cltv_pct": round(cltv, 1),
            "project_proceeds_usd": round(proceeds),
            "io_reserve_usd": round(io), "maturity_reserve_usd": round(reserve),
            "surety_premium_usd": round(surety_cost), "ae_fee_usd": round(fee),
            "b_to_hft_usd": round(b * 0.357),
            "ltv_alert": ltv_check["alert"], "ltv_alert_msg": ltv_check["message"],
        }

    def stress(self, noi, ds, tpc, debt) -> dict:
        cases = {
            "base":         (0,   0,  0,  "All assumptions as modeled"),
            "downside":     (-15, 10, 0,  "-15% revenue · +10% costs"),
            "stress":       (-25, 20, 6,  "-25% revenue · +20% costs · +6mo delay"),
            "catastrophic": (-40, 30, 0,  "-40% revenue — COVID/hurricane scenario"),
        }
        out = {}
        for name, (rev, cost, delay, desc) in cases.items():
            adj_noi = noi * (1 + rev / 100) - debt * 0.07 * delay / 12
            adj_ds = ds * (1 + cost / 200)
            dscr = round(adj_noi / adj_ds, 3) if adj_ds > 0 else 0
            out[name] = {
                "description": desc, "shocked_noi_usd": round(max(0, adj_noi)),
                "dscr": dscr,
                "status": "green" if dscr >= 1.5 else "yellow" if dscr >= 1.2 else "red" if dscr >= 1.0 else "critical",
                "surety_triggered": dscr < 1.0,
                "surety_draw_usd": round(max(0, (adj_ds - adj_noi) * 12)) if dscr < 1.0 else 0,
                "outcome": ("Performing as structured" if dscr >= 1.5 else
                            "Covenant breach — cure period" if dscr >= 1.2 else
                            "Reserve activation" if dscr >= 1.0 else
                            "Surety draw required — bond protected"),
            }
        return out

    def call_put_analysis(self, current_rate_bps, orig_rate_bps, deal: dict) -> dict:
        rate_change = current_rate_bps - orig_rate_bps
        recommendation = (
            "EXECUTE_CALL" if rate_change <= -CALL_TRIGGER_BPS else
            "CALL_ELIGIBLE" if rate_change <= -25 else
            "PUT_ALERT" if rate_change >= PUT_TRIGGER_BPS else
            "MONITOR" if rate_change >= 25 else "HOLD"
        )
        face = deal.get("bond_face_usd", 0)
        est_saving = face * abs(rate_change) / 10000 if rate_change < 0 else 0
        refi_fee = face * REFI_FEE_PCT / 100
        return {
            "recommendation": recommendation,
            "rate_change_bps": rate_change,
            "estimated_client_saving_usd": round(est_saving),
            "arrangement_fee_usd": round(refi_fee),
            "net_client_benefit_usd": round(est_saving - refi_fee),
            "blockchain_event": "CALL_TRIGGERED" if recommendation == "EXECUTE_CALL" else "MONITORING",
            "apex_action": "ACTIVATE_SHORT" if recommendation == "PUT_ALERT" else None,
        }


# ══════════════════════════════════════════════════════════════
# ENGINE 2: HFT ENGINE
# ══════════════════════════════════════════════════════════════
class HFTEngine:
    STRATEGIES = [
        {"name": "Treasury arbitrage",     "weight": 0.30, "target": 0.18, "risk": "low"},
        {"name": "Agency MBS basis",       "weight": 0.25, "target": 0.22, "risk": "low"},
        {"name": "Corp bond momentum",     "weight": 0.20, "target": 0.28, "risk": "medium"},
        {"name": "Rate vol capture",       "weight": 0.15, "target": 0.35, "risk": "medium"},
        {"name": "Cross-market stat arb",  "weight": 0.10, "target": 0.45, "risk": "high"},
    ]

    def simulate(self, aum: float, months: int = 12) -> dict:
        import random
        monthly, growth = [], []
        current = aum
        b_coupon_annual = aum * 0.11
        for m in range(months):
            mr = sum(s["weight"] * (s["target"] / 12 + random.gauss(0, s["target"] / 12 * 0.25))
                     for s in self.STRATEGIES)
            current *= (1 + mr)
            monthly.append(round(mr * 100, 3))
            growth.append(round(current))
        gross = current - aum
        surplus = max(0, gross - b_coupon_annual)
        ytd = round((current - aum) / aum * 100, 2)
        lc = current * 0.80
        phase = ("phase_4" if current >= 80e6 else "phase_3" if current >= 40e6
                 else "phase_2" if current >= 15e6 else "phase_1")
        return {
            "aum_start": round(aum), "aum_current": round(current),
            "ytd_return_pct": ytd, "gross_return_usd": round(gross),
            "b_coupon_serviced_usd": round(b_coupon_annual),
            "war_chest_surplus_usd": round(surplus),
            "effective_b_cost_pct": round(max(0, (b_coupon_annual - gross) / aum * 100), 2),
            "lc_capacity_usd": round(lc), "lc_phase": phase,
            "monthly_returns": monthly, "aum_growth": growth,
            "strategies": self.STRATEGIES,
            "ma_deployment_available": round(surplus * 0.6),
        }


# ══════════════════════════════════════════════════════════════
# ENGINE 3: RISK ENGINE
# ══════════════════════════════════════════════════════════════
class RiskEngine:
    DIMENSIONS = {
        "market":        {"weight": 0.20, "desc": "Rate + spread environment"},
        "construction":  {"weight": 0.20, "desc": "Cost + schedule + GC quality"},
        "credit":        {"weight": 0.20, "desc": "DSCR + LTV + leverage"},
        "operational":   {"weight": 0.15, "desc": "Occupancy + NOI + management"},
        "regulatory":    {"weight": 0.10, "desc": "Licensing + permits + compliance"},
        "sponsor":       {"weight": 0.10, "desc": "Financial health + track record"},
        "environmental": {"weight": 0.05, "desc": "Flood + hazmat + climate"},
    }

    def score_deal(self, deal: dict, metrics: dict) -> dict:
        scores = {}
        dscr = metrics.get("dscr", 0)
        ltv  = metrics.get("ltv_pct", 100)

        cr = (80 if dscr >= 2.0 else 65 if dscr >= 1.75 else 50 if dscr >= 1.5
              else 30 if dscr >= 1.25 else 10)
        cr += (20 if ltv <= 55 else 15 if ltv <= 65 else 10 if ltv <= 70
               else 5 if ltv <= 75 else 0)
        scores["credit"] = {"score": min(100, cr), "level": "green" if cr >= 70 else "yellow" if cr >= 45 else "red"}

        mr = deal.get("market_risk_score", 65)
        scores["market"] = {"score": mr, "level": "green" if mr >= 70 else "yellow" if mr >= 45 else "red"}

        delay = deal.get("construction_delay_months", 0)
        budget_var = deal.get("budget_variance_pct", 0)
        constr = max(0, 100 - delay * 8 - budget_var * 3)
        scores["construction"] = {"score": round(constr), "level": "green" if constr >= 70 else "yellow" if constr >= 45 else "red"}

        occ = deal.get("occupancy_pct", 85)
        op = min(100, occ + (10 if occ >= 88 else 0))
        scores["operational"] = {"score": round(op), "level": "green" if op >= 70 else "yellow" if op >= 45 else "red"}

        for dim in ["regulatory", "sponsor", "environmental"]:
            s = deal.get(f"{dim}_risk_score", 70)
            scores[dim] = {"score": s, "level": "green" if s >= 70 else "yellow" if s >= 45 else "red"}

        composite = sum(scores[d]["score"] * self.DIMENSIONS[d]["weight"] for d in scores)
        level = "green" if composite >= 70 else "yellow" if composite >= 45 else "red" if composite >= 25 else "critical"

        return {
            "composite_score": round(composite, 1),
            "risk_level": level,
            "dimension_scores": scores,
            "ltv_risk": check_ltv(ltv),
            "recommended_actions": self._actions(level, scores, deal),
        }

    def _actions(self, level, scores, deal) -> list:
        actions = []
        if scores.get("credit", {}).get("level") == "red":
            actions.append({"priority": "critical", "action": "Restructure debt — DSCR below 1.25x", "agent": "sentinel"})
        if scores.get("construction", {}).get("level") == "red":
            actions.append({"priority": "high", "action": "Contact Hylant — performance bond evaluation", "agent": "surety_scout"})
        if deal.get("ltv_pct", 0) > LTV_ALERT:
            actions.append({"priority": "critical", "action": f"LTV {deal.get('ltv_pct', 0):.1f}% exceeds threshold — restructure required", "agent": "maxwell"})
        if level in ["red", "critical"]:
            actions.append({"priority": "high", "action": "Generate risk memo for bond counsel", "agent": "morgan"})
        return actions


# ══════════════════════════════════════════════════════════════
# ENGINE 4: MA ENGINE
# ══════════════════════════════════════════════════════════════
class MAEngine:
    def bridge_economics(self, company_ev: float, revenue: float) -> dict:
        bridge_eq_pct = (MA_BRIDGE_EQ_MIN + MA_BRIDGE_EQ_MAX) / 2
        nest_eq_pct   = (MA_EQUITY_MIN + MA_EQUITY_MAX) / 2
        surety_pct    = (SURETY_FEE_MIN + SURETY_FEE_MAX) / 2
        bridge_capital = company_ev * bridge_eq_pct / 100
        surety_fee     = company_ev * surety_pct / 100
        packaging_fee  = company_ev * PACKAGING_FEE / 100
        nest_equity_usd = company_ev * nest_eq_pct / 100
        total_fees = surety_fee + packaging_fee
        return {
            "company_ev_usd": round(company_ev),
            "bridge_capital_usd": round(bridge_capital),
            "bridge_equity_pct": bridge_eq_pct,
            "nest_equity_retained_pct": nest_eq_pct,
            "nest_equity_retained_usd": round(nest_equity_usd),
            "surety_fee_usd": round(surety_fee),
            "surety_fee_pct": surety_pct,
            "packaging_fee_usd": round(packaging_fee),
            "packaging_fee_pct": PACKAGING_FEE,
            "total_fees_usd": round(total_fees),
            "nest_total_economics_usd": round(total_fees + nest_equity_usd),
            "irr_target_pct": 28.0,
            "hold_period_years": 5,
        }

    def irr_matrix(self, ebitda, entry_mult, exit_mult,
                   growth, debt_pct=0.50) -> dict:
        entry_ev = ebitda * entry_mult
        nest_eq  = entry_ev * (1 - debt_pct) * 0.25
        matrix = {}
        for sc, m in [("low", 0.75), ("base", 1.0), ("high", 1.25)]:
            matrix[sc] = {}
            for yr in [3, 5, 7]:
                ex_ebitda = ebitda * ((1 + growth * m) ** yr)
                ex_ev = ex_ebitda * exit_mult * m
                ex_eq = ex_ev * (1 - debt_pct * 0.5) * 0.25
                irr = (ex_eq / nest_eq) ** (1 / yr) - 1 if nest_eq > 0 and ex_eq > 0 else 0
                matrix[sc][f"yr{yr}"] = {
                    "irr_pct": round(irr * 100, 1),
                    "moic": round(ex_eq / nest_eq, 2) if nest_eq > 0 else 0,
                    "nest_return_usd": round(ex_eq),
                    "exit_ev_usd": round(ex_ev),
                    "color": "green" if irr > 0.25 else "yellow" if irr > 0.15 else "red",
                }
        return {"entry_ev": round(entry_ev), "nest_equity": round(nest_eq),
                "scenarios": matrix, "preferred": "base_yr5"}


# ══════════════════════════════════════════════════════════════
# ENGINE 5: SURETY ENGINE
# ══════════════════════════════════════════════════════════════
class SuretyEngine:
    PROVIDERS = [
        {"name": "Hylant Insurance", "type": "performance_surety", "premium_pct": 8.5,
         "max_bond_usd": 500_000_000, "rating": "A+", "primary": True},
        {"name": "Travelers Bond", "type": "payment_surety", "premium_pct": 7.5,
         "max_bond_usd": 300_000_000, "rating": "AA", "primary": False},
        {"name": "Liberty Mutual Surety", "type": "dual_wrap", "premium_pct": 9.5,
         "max_bond_usd": 750_000_000, "rating": "A", "primary": False},
    ]

    def analyze(self, deal: dict, metrics: dict) -> dict:
        face = deal.get("bond_face_usd", deal.get("a_tranche_usd", 0))
        dscr  = metrics.get("dscr", 1.5)
        ltv   = metrics.get("ltv_pct", 70)
        primary = self.PROVIDERS[0]
        premium = face * primary["premium_pct"] / 100
        dual_wrap_premium = face * 0.03
        parametric_trigger = dscr < 1.2 or ltv > LTV_ALERT
        lc_rate = 0.0075 * face
        return {
            "primary_provider": primary["name"],
            "primary_premium_usd": round(premium),
            "primary_premium_pct": primary["premium_pct"],
            "dual_wrap_premium_usd": round(dual_wrap_premium),
            "total_surety_cost_usd": round(premium + dual_wrap_premium),
            "lc_eligible": True,
            "lc_annual_cost_usd": round(lc_rate),
            "parametric_insurance_triggered": parametric_trigger,
            "parametric_trigger_reason": (
                "DSCR below 1.2x" if dscr < 1.2 else
                f"LTV {ltv:.1f}% exceeds {LTV_ALERT}%" if ltv > LTV_ALERT else None
            ),
            "hylant_submission_ready": self._check_hylant(deal),
            "providers": self.PROVIDERS,
        }

    def _check_hylant(self, deal: dict) -> dict:
        required = ["appraisal", "phase_i_environmental", "gmp_contract",
                     "sponsor_financials", "proforma", "feasibility_study"]
        checklist = deal.get("document_checklist", {})
        missing = [r for r in required if not checklist.get(r)]
        return {"ready": len(missing) == 0, "missing_items": missing,
                "completion_pct": round((len(required) - len(missing)) / len(required) * 100)}


# ══════════════════════════════════════════════════════════════
# ENGINE 6: DOCUMENT PARSER
# ══════════════════════════════════════════════════════════════
class DocumentParser:
    DOC_TYPES = ["proforma", "appraisal", "phase_i_environmental", "tax_returns",
                 "audited_financials", "gmp_contract", "feasibility_study",
                 "title_report", "entity_docs", "bank_statements"]

    def classify(self, text_sample: str) -> str:
        text_lower = text_sample.lower()
        if any(w in text_lower for w in ["net operating income", "noi", "occupancy ramp", "revenue per unit"]):
            return "proforma"
        if any(w in text_lower for w in ["appraisal", "uspap", "market value", "capitalization rate"]):
            return "appraisal"
        if any(w in text_lower for w in ["phase i", "environmental", "recognized environmental"]):
            return "phase_i_environmental"
        if any(w in text_lower for w in ["adjusted gross income", "schedule c", "form 1040", "w-2"]):
            return "tax_returns"
        if any(w in text_lower for w in ["certified public", "independent auditor", "gaap", "balance sheet"]):
            return "audited_financials"
        if any(w in text_lower for w in ["guaranteed maximum price", "gmp", "general contractor", "subcontractor"]):
            return "gmp_contract"
        if any(w in text_lower for w in ["market feasibility", "demand analysis", "absorption", "competitive set"]):
            return "feasibility_study"
        return "unknown"

    def extract_with_claude(self, content: str, doc_type: str) -> dict:
        prompts = {
            "proforma": "Extract from this proforma: monthly NOI for 36 months (array), stabilized NOI, stabilized occupancy %, total project cost, debt service, DSCR at stabilization. Return JSON only.",
            "appraisal": "Extract: appraised value USD, capitalization rate %, effective date, appraiser name, comparable sales (array with address/price/cap_rate). Return JSON only.",
            "audited_financials": "Extract: total assets, total liabilities, net worth, EBITDA, revenue, net income, funded debt, off-balance-sheet items. Return JSON only.",
            "gmp_contract": "Extract: GMP amount USD, contractor name, completion date, contingency amount, key milestones (array). Return JSON only.",
        }
        prompt = prompts.get(doc_type, f"Extract all financial data from this {doc_type} document. Return JSON only.")
        raw = call_claude(f"{prompt}\n\nDOCUMENT:\n{content[:6000]}")
        try:
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            return json.loads(json_match.group()) if json_match else {"raw": raw}
        except Exception:
            return {"raw": raw, "parse_error": True}

    def spread_proforma(self, data: dict) -> dict:
        monthly_noi = data.get("monthly_noi", [])
        if not monthly_noi:
            ebitda = data.get("stabilized_noi", 0)
            monthly_noi = [round(ebitda * 0.3 + ebitda * 0.7 * (i / 35) ** 0.8)
                           for i in range(36)]
        ramp = [{"month": i + 1, "noi": v, "occupancy_pct": min(95, 30 + (65 * i / 35))}
                for i, v in enumerate(monthly_noi)]
        return {"monthly_ramp": ramp, "stabilized_noi": max(monthly_noi) if monthly_noi else 0,
                "break_even_month": next((i + 1 for i, v in enumerate(monthly_noi) if v > 0), 12)}


# ── SINGLETON EXPORTS (import these everywhere) ───────────────
credit  = CreditEngine()
hft     = HFTEngine()
risk    = RiskEngine()
ma_eng  = MAEngine()
surety  = SuretyEngine()
docs    = DocumentParser()
