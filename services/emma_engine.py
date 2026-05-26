"""
NEST EMMA Engine — Deep integration with MSRB's Electronic Municipal Market Access.

EMMA is the single richest source of structured bond data in existence.
Every muni bond that has ever been issued, structured, rated, insured,
and funded is documented there.

This engine:
1. Searches EMMA for bonds by issuer, CUSIP, state, sector
2. Parses Official Statements into structured bond profiles using Claude AI
3. Generates sector-specific default templates from aggregated parsed bonds
4. Provides comparable transaction analysis
5. Polls for new filings (public search now, SOAP subscription later)

MSRB Subscription Services (future):
- Primary Market: https://services.emma.msrb.org/SubscriptionServices/PrimaryMarketSubscriptionService.svc
- Continuing Disclosure: https://services.emma.msrb.org/SubscriptionServices/ContinuingDisclosureSubscriptionService.svc
- Transaction Data: real-time trade feed ($11K/yr)
- Polling interval: every 5 minutes recommended
"""
from __future__ import annotations

import logging
import statistics
from datetime import datetime
from typing import Any

import httpx

from agents._claude import complete

log = logging.getLogger(__name__)

EMMA_SEARCH_URL = "https://emma.msrb.org"
USER_AGENT = "NEST Advisors Platform sean@ardencapital.com"

# ── Bond Structure Schema ─────────────────────────────────────

BOND_STRUCTURE_FIELDS = [
    "cusip", "issuer", "borrower", "state", "sector", "naics_code",
    "par_amount", "coupon_rate", "dated_date", "maturity_date",
    "tax_status", "security_type", "bond_type", "amortization",
    "call_schedule", "covenant_package", "reserves", "enhancement",
    "ratings", "counterparties", "parsed_at", "source_url",
]

# ── Sector mapping for NAICS-driven lookups ───────────────────

SECTOR_NAICS_MAP = {
    "hospitals": ["622110", "622310"],
    "senior_living": ["623311", "623312", "623110"],
    "charter_schools": ["611110"],
    "higher_education": ["611310"],
    "affordable_multifamily": ["531110"],
    "market_rate_multifamily": ["531110"],
    "hotels_hospitality": ["721110"],
    "data_centers": ["518210"],
    "solid_waste": ["562212"],
    "water_sewer": ["221310", "221320"],
    "electric_power": ["221110"],
    "airports": ["488119"],
    "manufacturing": ["31", "32", "33"],
}

# ── In-Memory Bond Structure Database ─────────────────────────
# Persisted to disk later; in-memory list for now.

PARSED_BONDS: list[dict[str, Any]] = []


# ── OS Parser Prompt ──────────────────────────────────────────

OS_PARSER_PROMPT = """You are a bond document parser for NEST Advisors, a digital investment bank.

Given the text of a municipal bond Official Statement (OS), extract the following fields into a JSON object:

{
  "cusip": "string or null",
  "issuer": "issuing authority name",
  "borrower": "borrower/obligor name",
  "state": "two-letter state code",
  "sector": "one of: hospitals, senior_living, charter_schools, higher_education, affordable_multifamily, market_rate_multifamily, hotels_hospitality, data_centers, solid_waste, water_sewer, electric_power, airports, manufacturing, corporate, other",
  "naics_code": "NAICS code if identifiable",
  "par_amount": number (in dollars),
  "coupon_rate": number (as percentage, e.g. 5.25),
  "dated_date": "YYYY-MM-DD",
  "maturity_date": "YYYY-MM-DD (final maturity)",
  "tax_status": "tax_exempt | taxable | amt",
  "security_type": "revenue | go | pab_501c3 | pab_142 | conduit | corporate",
  "bond_type": "serial | term | variable_rate | combination",
  "amortization": "level_debt_service | ascending | bullet | custom | serial_with_term",
  "call_schedule": [{"date": "YYYY-MM-DD", "price": 100.0, "type": "optional | mandatory | make_whole"}],
  "covenant_package": {
    "dscr_threshold": number or null,
    "additional_bonds_test": "description or null",
    "restricted_payments": "description or null",
    "distribution_trap": number or null
  },
  "reserves": {
    "dsrf": number (dollar amount),
    "dsrf_type": "mads | 125pct_avg | 10pct_proceeds | other",
    "operating_reserve": number or null,
    "cap_i_reserve": number or null
  },
  "enhancement": {
    "type": "none | bond_insurance | loc | surety | federal_guarantee",
    "provider": "name or null",
    "enhanced_rating": "rating or null"
  },
  "ratings": {
    "moodys": "rating or null",
    "sp": "rating or null",
    "fitch": "rating or null",
    "kbra": "rating or null"
  },
  "counterparties": {
    "trustee": "name or null",
    "bond_counsel": "name or null",
    "underwriter": "name or null",
    "financial_advisor": "name or null"
  }
}

Return ONLY the JSON object. No explanation. If a field cannot be determined, use null.
"""


class EMMAEngine:
    """Deep EMMA integration — search, parse, template generation, comps."""

    def __init__(self):
        self._client_timeout = 15

    # ── Search ────────────────────────────────────────────────

    def search(
        self,
        issuer: str = "",
        cusip: str = "",
        state: str = "",
        sector: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """Search EMMA for municipal bond issues.

        Uses EMMA public search. When MSRB subscription is active,
        switches to the SOAP API for real-time data.
        """
        try:
            params = {}
            if cusip:
                params["cusip"] = cusip
            elif issuer:
                params["issuerName"] = issuer
            else:
                params["issuerName"] = sector or "revenue bond"

            if state:
                params["state"] = state.upper()

            with httpx.Client(timeout=self._client_timeout) as c:
                r = c.get(
                    f"{EMMA_SEARCH_URL}/api/v1/search",
                    params=params,
                    headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                )
                if r.status_code == 200:
                    data = r.json()
                    results = data if isinstance(data, list) else data.get("results", [])
                    return results[:limit]
                else:
                    log.warning("EMMA search returned %d", r.status_code)
                    return []
        except Exception as e:
            log.error("EMMA search error: %s", e)
            return []

    # ── Official Statement Parser ─────────────────────────────

    def parse_official_statement(self, text: str, source_url: str = "") -> dict:
        """Parse an Official Statement into structured bond profile using Claude AI.

        This is the core intelligence function. Given raw OS text, extracts
        30+ structural fields into the Bond Structure Schema.
        """
        if len(text) > 50000:
            text = text[:50000] + "\n\n[TRUNCATED — document exceeds 50,000 characters]"

        response = complete(
            OS_PARSER_PROMPT,
            f"Parse this Official Statement:\n\n{text}",
            max_tokens=4096,
        )

        try:
            import json
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                clean = clean.rsplit("```", 1)[0]
            parsed = json.loads(clean)
        except (json.JSONDecodeError, Exception) as e:
            log.error("Failed to parse OS response as JSON: %s", e)
            parsed = {"error": str(e), "raw_response": response[:500]}

        parsed["parsed_at"] = datetime.utcnow().isoformat()
        parsed["source_url"] = source_url

        PARSED_BONDS.append(parsed)
        return parsed

    # ── Template Generator ────────────────────────────────────

    def generate_template(
        self,
        sector: str,
        min_par: float = 0,
        max_par: float = float("inf"),
    ) -> dict:
        """Generate a default bond structure template from parsed bonds.

        Aggregates parsed bonds matching the sector and size range,
        extracts the most common structural patterns.
        """
        matching = [
            b for b in PARSED_BONDS
            if b.get("sector") == sector
            and (min_par <= (b.get("par_amount") or 0) <= max_par)
            and "error" not in b
        ]

        if not matching:
            return self._static_template(sector)

        coupons = [b["coupon_rate"] for b in matching if b.get("coupon_rate")]
        pars = [b["par_amount"] for b in matching if b.get("par_amount")]
        dscrs = [
            b["covenant_package"]["dscr_threshold"]
            for b in matching
            if b.get("covenant_package", {}).get("dscr_threshold")
        ]

        amort_counts: dict[str, int] = {}
        for b in matching:
            a = b.get("amortization", "unknown")
            amort_counts[a] = amort_counts.get(a, 0) + 1
        common_amort = max(amort_counts, key=amort_counts.get) if amort_counts else "level_debt_service"

        enhance_counts: dict[str, int] = {}
        for b in matching:
            e = (b.get("enhancement") or {}).get("type", "none")
            enhance_counts[e] = enhance_counts.get(e, 0) + 1
        common_enhance = max(enhance_counts, key=enhance_counts.get) if enhance_counts else "none"

        tax_counts: dict[str, int] = {}
        for b in matching:
            t = b.get("tax_status", "unknown")
            tax_counts[t] = tax_counts.get(t, 0) + 1
        common_tax = max(tax_counts, key=tax_counts.get) if tax_counts else "tax_exempt"

        return {
            "sector": sector,
            "sample_size": len(matching),
            "template": {
                "par_range": {"min": min(pars) if pars else 0, "max": max(pars) if pars else 0, "median": statistics.median(pars) if pars else 0},
                "coupon_range": {"min": min(coupons) if coupons else 0, "max": max(coupons) if coupons else 0, "median": round(statistics.median(coupons), 3) if coupons else 0},
                "typical_amortization": common_amort,
                "typical_tax_status": common_tax,
                "typical_enhancement": common_enhance,
                "covenant_package": {
                    "dscr_threshold": round(statistics.median(dscrs), 2) if dscrs else 1.20,
                },
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _static_template(self, sector: str) -> dict:
        """Fallback templates from Operating Framework + Bible when no parsed bonds exist."""
        defaults = {
            "senior_living": {
                "par_range": {"min": 20_000_000, "max": 150_000_000, "median": 50_000_000},
                "coupon_range": {"min": 4.50, "max": 7.00, "median": 5.50},
                "typical_amortization": "level_debt_service",
                "typical_tax_status": "tax_exempt",
                "typical_enhancement": "bond_insurance",
                "security_type": "pab_501c3",
                "covenant_package": {"dscr_threshold": 1.20, "additional_bonds_test": "1.20x historical, 1.10x projected", "distribution_trap": 1.10},
                "reserves": {"dsrf_type": "mads", "operating_reserve_months": 3, "cap_i_months": 24},
                "call_schedule": {"nc_period_years": 10, "par_call_after": True},
                "maturity_years": 30,
            },
            "affordable_multifamily": {
                "par_range": {"min": 10_000_000, "max": 80_000_000, "median": 30_000_000},
                "coupon_range": {"min": 4.00, "max": 6.50, "median": 5.00},
                "typical_amortization": "level_debt_service",
                "typical_tax_status": "tax_exempt",
                "typical_enhancement": "federal_guarantee",
                "security_type": "pab_142",
                "covenant_package": {"dscr_threshold": 1.15, "additional_bonds_test": "1.15x projected"},
                "reserves": {"dsrf_type": "mads"},
                "call_schedule": {"nc_period_years": 10, "par_call_after": True},
                "maturity_years": 35,
            },
            "hospitals": {
                "par_range": {"min": 30_000_000, "max": 300_000_000, "median": 80_000_000},
                "coupon_range": {"min": 4.00, "max": 6.00, "median": 5.00},
                "typical_amortization": "serial_with_term",
                "typical_tax_status": "tax_exempt",
                "typical_enhancement": "none",
                "security_type": "pab_501c3",
                "covenant_package": {"dscr_threshold": 1.25, "days_cash_on_hand": 90},
                "reserves": {"dsrf_type": "mads"},
                "call_schedule": {"nc_period_years": 10, "par_call_after": True},
                "maturity_years": 30,
            },
            "charter_schools": {
                "par_range": {"min": 5_000_000, "max": 50_000_000, "median": 20_000_000},
                "coupon_range": {"min": 5.00, "max": 7.50, "median": 6.25},
                "typical_amortization": "level_debt_service",
                "typical_tax_status": "tax_exempt",
                "typical_enhancement": "none",
                "security_type": "pab_501c3",
                "covenant_package": {"dscr_threshold": 1.10, "enrollment_covenant": True},
                "reserves": {"dsrf_type": "mads"},
                "call_schedule": {"nc_period_years": 10, "par_call_after": True},
                "maturity_years": 30,
            },
            "corporate_ma": {
                "par_range": {"min": 10_000_000, "max": 300_000_000, "median": 50_000_000},
                "coupon_range": {"min": 7.00, "max": 10.00, "median": 8.50},
                "typical_amortization": "bullet",
                "typical_tax_status": "taxable",
                "typical_enhancement": "none",
                "security_type": "corporate",
                "covenant_package": {"dscr_threshold": 1.20, "leverage_ceiling": 5.5, "restricted_payments": "standard_high_yield"},
                "reserves": {"dsrf_type": "mads", "cap_i_months": 18},
                "call_schedule": {"nc_period_years": 3, "step_down_premium": True},
                "maturity_years": 7,
            },
        }
        template = defaults.get(sector, defaults["corporate_ma"])
        return {
            "sector": sector,
            "sample_size": 0,
            "source": "Operating Framework static defaults",
            "template": template,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ── Comparable Transactions ───────────────────────────────

    def find_comps(
        self,
        sector: str = "",
        min_par: float = 0,
        max_par: float = float("inf"),
        rating: str = "",
        state: str = "",
        tax_status: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """Find comparable bond transactions from parsed bond database."""
        results = []
        for bond in PARSED_BONDS:
            if "error" in bond:
                continue
            if sector and bond.get("sector") != sector:
                continue
            par = bond.get("par_amount") or 0
            if par < min_par or par > max_par:
                continue
            if state and bond.get("state", "").upper() != state.upper():
                continue
            if tax_status and bond.get("tax_status") != tax_status:
                continue
            if rating:
                ratings = bond.get("ratings", {})
                bond_ratings = [v for v in ratings.values() if v]
                if rating.upper() not in [r.upper() for r in bond_ratings]:
                    continue
            results.append(bond)

        results.sort(key=lambda b: abs((b.get("par_amount") or 0) - ((min_par + max_par) / 2)))
        return results[:limit]

    # ── Stats ─────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return parsed bond database statistics."""
        valid = [b for b in PARSED_BONDS if "error" not in b]
        sector_counts: dict[str, int] = {}
        state_counts: dict[str, int] = {}
        for b in valid:
            s = b.get("sector", "unknown")
            sector_counts[s] = sector_counts.get(s, 0) + 1
            st = b.get("state", "unknown")
            state_counts[st] = state_counts.get(st, 0) + 1

        return {
            "total_parsed": len(PARSED_BONDS),
            "valid_parsed": len(valid),
            "errors": len(PARSED_BONDS) - len(valid),
            "by_sector": sector_counts,
            "by_state": state_counts,
        }

    # ── Polling (Public Search for now) ───────────────────────

    def poll(self, sector: str = "senior living", limit: int = 10) -> dict:
        """Poll EMMA for new filings. Public search for now; SOAP subscription later."""
        results = self.search(issuer=sector, limit=limit)
        return {
            "polled_at": datetime.utcnow().isoformat(),
            "mode": "public_search",
            "query": sector,
            "results_found": len(results),
            "results": results,
            "note": "SOAP subscription (Primary Market + Continuing Disclosure) enables real-time feed at $11K/yr per service",
        }
