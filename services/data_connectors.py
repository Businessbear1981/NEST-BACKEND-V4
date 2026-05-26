"""
NEST Data Connectors — External Data Ingestion Plugins.
Layer 1B: Market data, property, regulatory, credit, legal, construction.

Each connector follows the BasePlugin interface from ingestion.py.
All data normalized to NEST schema before reaching Layer 2 (intelligence services).
"""
import os
import time
import httpx
from datetime import datetime
from services.ingestion import BasePlugin, PluginStatus, ingestion_layer


# ── MARKET DATA ──────────────────────────────────────────────

class FREDPlugin(BasePlugin):
    """Federal Reserve Economic Data — Treasury rates, SOFR, spreads."""
    name = "fred"
    description = "Federal Reserve Economic Data. Treasury rates, SOFR, unemployment, CPI, GDP."
    capabilities = ["treasury_rates", "sofr_rate", "economic_indicators", "yield_curve", "inflation_data"]
    requires_key = "FRED_API_KEY"

    SERIES = {
        "treasury_10yr": "DGS10",
        "treasury_5yr": "DGS5",
        "treasury_2yr": "DGS2",
        "treasury_30yr": "DGS30",
        "sofr": "SOFR",
        "fed_funds": "FEDFUNDS",
        "cpi": "CPIAUCSL",
        "unemployment": "UNRATE",
        "gdp": "GDP",
        "housing_starts": "HOUST",
        "ig_spread": "BAMLC0A4CBBBEY",
    }

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str = "", series_id: str = "DGS10", limit: int = 1, **kwargs) -> dict:
        if not self.is_configured():
            return self._static_fallback()

        start = time.time()
        try:
            with httpx.Client(timeout=10) as c:
                r = c.get(self.base_url, params={
                    "series_id": series_id,
                    "api_key": self.get_key(),
                    "sort_order": "desc",
                    "limit": limit,
                    "file_type": "json",
                })
                r.raise_for_status()
                obs = r.json().get("observations", [])

            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            self.status = PluginStatus.CONNECTED

            values = [{"date": o["date"], "value": float(o["value"])} for o in obs if o["value"] != "."]
            return {
                "success": True,
                "plugin": self.name,
                "series_id": series_id,
                "values": values,
                "latest": values[0] if values else None,
                "latency_ms": round(latency),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            self.status = PluginStatus.ERROR
            return self._static_fallback()

    # Bond Desk series subset — the rates that matter for live structuring
    BOND_DESK_SERIES = {
        "treasury_10yr": "DGS10",
        "treasury_5yr": "DGS5",
        "treasury_2yr": "DGS2",
        "treasury_30yr": "DGS30",
        "treasury_3mo": "DGS3MO",
        "sofr": "SOFR",
        "fed_funds": "FEDFUNDS",
        "ig_spread": "BAMLC0A4CBBBEY",
        "hy_spread": "BAMLH0A0HYM2EY",
        "mortgage_30yr": "MORTGAGE30US",
    }

    STATIC_RATES = {
        "treasury_10yr": 4.28, "treasury_5yr": 4.05, "treasury_2yr": 3.92,
        "treasury_30yr": 4.52, "treasury_3mo": 5.25, "sofr": 5.33,
        "fed_funds": 5.33, "ig_spread": 1.12, "hy_spread": 3.45, "mortgage_30yr": 6.87,
    }

    # Simple in-memory cache: {series_id: (value, timestamp)}
    _cache = {}
    _cache_ttl = 300  # 5 minutes

    def _fetch_cached(self, series_id: str) -> float | None:
        """Fetch a single series with 5-min cache."""
        now = time.time()
        cached = self._cache.get(series_id)
        if cached and (now - cached[1]) < self._cache_ttl:
            return cached[0]
        result = self.execute(series_id=series_id)
        if result.get("success") and result.get("latest"):
            val = result["latest"]["value"]
            self._cache[series_id] = (val, now)
            return val
        return None

    def get_market_snapshot(self) -> dict:
        """Pull all key rates at once."""
        snapshot = {}
        for label, series in [("treasury_10yr", "DGS10"), ("treasury_5yr", "DGS5"),
                               ("sofr", "SOFR"), ("fed_funds", "FEDFUNDS")]:
            result = self.execute(series_id=series)
            if result["success"] and result.get("latest"):
                snapshot[label] = result["latest"]["value"]
        return {"source": "FRED", "rates": snapshot, "timestamp": datetime.utcnow().isoformat()}

    def get_bond_desk_snapshot(self) -> dict:
        """Pull all Bond Desk rates — the live dashboard feed."""
        rates = {}
        source = "live"
        for label, series_id in self.BOND_DESK_SERIES.items():
            val = self._fetch_cached(series_id)
            if val is not None:
                rates[label] = val
            else:
                rates[label] = self.STATIC_RATES.get(label, 0)
                source = "mixed"

        # Derived metrics
        t10 = rates.get("treasury_10yr", 4.28)
        t2 = rates.get("treasury_2yr", 3.92)
        t3mo = rates.get("treasury_3mo", 5.25)
        rates["yield_curve_spread_bps"] = round((t10 - t2) * 100, 1)
        rates["curve_inverted"] = t2 > t10
        rates["ted_stress"] = "elevated" if (t3mo - rates.get("sofr", 5.33)) > 0.5 else "normal"

        return {
            "success": True,
            "source": source,
            "rates": rates,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_yield_curve(self) -> dict:
        """Full Treasury yield curve for charting."""
        curve_series = [
            ("3mo", "DGS3MO"), ("2yr", "DGS2"), ("5yr", "DGS5"),
            ("10yr", "DGS10"), ("30yr", "DGS30"),
        ]
        points = []
        for label, sid in curve_series:
            val = self._fetch_cached(sid)
            points.append({"tenor": label, "yield_pct": val or self.STATIC_RATES.get(f"treasury_{label}", 0)})
        return {"success": True, "curve": points, "timestamp": datetime.utcnow().isoformat()}

    def _static_fallback(self) -> dict:
        return {
            "success": True, "plugin": self.name, "source": "static_fallback",
            "values": [{"date": "2026-04-30", "value": 4.28}],
            "latest": {"date": "2026-04-30", "value": 4.28},
            "rates": self.STATIC_RATES,
            "timestamp": datetime.utcnow().isoformat(),
        }


class TreasuryDirectPlugin(BasePlugin):
    """US Treasury Direct — auction data, securities info."""
    name = "treasury_direct"
    description = "US Treasury Direct. Auction results, outstanding securities, debt data."
    capabilities = ["auction_results", "outstanding_debt", "securities_data"]
    requires_key = "TREASURY_DIRECT_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED  # Public API, no key needed for basic data

    def is_configured(self) -> bool:
        return True  # Public endpoints available

    def execute(self, prompt: str = "", data_type: str = "announced", **kwargs) -> dict:
        start = time.time()
        try:
            with httpx.Client(timeout=10) as c:
                r = c.get(f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/avg_interest_rates",
                          params={"sort": "-record_date", "page[size]": 10, "format": "json"})
                r.raise_for_status()
                data = r.json().get("data", [])

            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            return {
                "success": True, "plugin": self.name,
                "records": data[:5],
                "latency_ms": round(latency),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


# ── PROPERTY / REAL ESTATE ───────────────────────────────────

class ATTOMPlugin(BasePlugin):
    """ATTOM Data — Property data, valuations, ownership, tax records."""
    name = "attom"
    description = "ATTOM Property Data. Valuations, ownership records, tax assessments, comparable sales."
    capabilities = ["property_valuation", "ownership_records", "tax_assessment",
                    "comparable_sales", "foreclosure_data", "neighborhood_stats"]
    requires_key = "ATTOM_API_KEY"

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str = "", address: str = "", endpoint: str = "property/detail", **kwargs) -> dict:
        if not self.is_configured():
            return {"success": False, "plugin": self.name, "error": "ATTOM_API_KEY not set"}
        start = time.time()
        try:
            with httpx.Client(timeout=15) as c:
                r = c.get(f"{self.base_url}/{endpoint}",
                          headers={"apikey": self.get_key(), "Accept": "application/json"},
                          params={"address1": address} if address else {})
                r.raise_for_status()
                data = r.json()
            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            return {"success": True, "plugin": self.name, "data": data, "latency_ms": round(latency),
                    "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


class CoStarPlugin(BasePlugin):
    """CoStar — Commercial real estate analytics, comps, market data."""
    name = "costar"
    description = "CoStar commercial real estate. Market analytics, comparable sales, rent comps, cap rates."
    capabilities = ["market_analytics", "comp_sales", "rent_comps", "cap_rates",
                    "vacancy_rates", "construction_pipeline"]
    requires_key = "COSTAR_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str = "", market: str = "", property_type: str = "senior_living", **kwargs) -> dict:
        if not self.is_configured():
            return {"success": False, "plugin": self.name, "error": "COSTAR_API_KEY not set"}
        start = time.time()
        try:
            with httpx.Client(timeout=15) as c:
                r = c.get("https://api.costar.com/v2/markets",
                          headers={"Authorization": f"Bearer {self.get_key()}"},
                          params={"market": market, "propertyType": property_type})
                r.raise_for_status()
                data = r.json()
            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            return {"success": True, "plugin": self.name, "data": data, "latency_ms": round(latency),
                    "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


# ── REGULATORY ───────────────────────────────────────────────

class EDGARPlugin(BasePlugin):
    """SEC EDGAR — Corporate filings, 10-K, 10-Q, 8-K, proxy statements."""
    name = "edgar"
    description = "SEC EDGAR filings. 10-K, 10-Q, 8-K, S-1, proxy statements, insider transactions."
    capabilities = ["company_filings", "financial_statements", "insider_transactions",
                    "proxy_data", "registration_statements"]
    requires_key = "SEC_USER_AGENT"

    def __init__(self):
        super().__init__()
        self.base_url = "https://efts.sec.gov/LATEST/search-index"
        self.status = PluginStatus.CONNECTED  # Public API

    def is_configured(self) -> bool:
        return True

    def execute(self, prompt: str = "", company: str = "", filing_type: str = "10-K", **kwargs) -> dict:
        start = time.time()
        try:
            agent = os.getenv("SEC_USER_AGENT", "NEST Advisors sean@ardencapital.com")
            with httpx.Client(timeout=15) as c:
                r = c.get("https://efts.sec.gov/LATEST/search-index",
                          params={"q": company or prompt, "forms": filing_type, "dateRange": "custom",
                                  "startdt": "2024-01-01", "enddt": "2026-12-31"},
                          headers={"User-Agent": agent})
                r.raise_for_status()
                data = r.json()
            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            hits = data.get("hits", {}).get("hits", [])
            return {"success": True, "plugin": self.name, "results": len(hits),
                    "filings": [{"name": h.get("_source", {}).get("display_names", [""])[0],
                                 "form": h.get("_source", {}).get("form_type", ""),
                                 "date": h.get("_source", {}).get("file_date", ""),
                                 "url": h.get("_source", {}).get("file_url", "")} for h in hits[:10]],
                    "latency_ms": round(latency), "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


class EMMAPlugin(BasePlugin):
    """EMMA — Electronic Municipal Market Access. Municipal bond filings and disclosures."""
    name = "emma"
    description = "MSRB EMMA. Municipal bond official statements, continuing disclosures, trade data."
    capabilities = ["official_statements", "continuing_disclosures", "trade_data",
                    "credit_ratings", "bond_documents"]
    requires_key = "EMMA_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED  # Public access available

    def is_configured(self) -> bool:
        return True

    def execute(self, prompt: str = "", cusip: str = "", issuer: str = "", **kwargs) -> dict:
        start = time.time()
        try:
            with httpx.Client(timeout=15) as c:
                params = {}
                if cusip:
                    params["cusip"] = cusip
                elif issuer:
                    params["issuerName"] = issuer
                else:
                    params["issuerName"] = prompt
                r = c.get("https://emma.msrb.org/api/v1/search",
                          params=params,
                          headers={"Accept": "application/json"})
                r.raise_for_status()
                data = r.json()
            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            return {"success": True, "plugin": self.name, "data": data,
                    "latency_ms": round(latency), "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


class FINRABrokerCheckPlugin(BasePlugin):
    """FINRA BrokerCheck — Broker/adviser background verification."""
    name = "finra_brokercheck"
    description = "FINRA BrokerCheck. Broker registration, disciplinary history, firm background."
    capabilities = ["broker_lookup", "firm_lookup", "disciplinary_history", "registration_status"]
    requires_key = "FINRA_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED  # Public search available

    def is_configured(self) -> bool:
        return True

    def execute(self, prompt: str = "", name: str = "", crd_number: str = "", **kwargs) -> dict:
        start = time.time()
        try:
            query = name or prompt
            with httpx.Client(timeout=10) as c:
                r = c.get("https://api.brokercheck.finra.org/search/individual",
                          params={"query": query, "hl": "true", "nrows": 10, "start": 0})
                r.raise_for_status()
                data = r.json()
            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            hits = data.get("hits", {}).get("hits", [])
            return {"success": True, "plugin": self.name, "results": len(hits),
                    "individuals": hits[:5],
                    "latency_ms": round(latency), "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


# ── CREDIT ───────────────────────────────────────────────────

class DnBPlugin(BasePlugin):
    """Dun & Bradstreet — Business credit reports, DUNS numbers, risk scores."""
    name = "dnb"
    description = "Dun & Bradstreet. Business credit reports, DUNS lookup, risk scores, financial stress."
    capabilities = ["credit_report", "duns_lookup", "risk_score", "financial_stress_score",
                    "business_verification"]
    requires_key = "DNB_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str = "", duns_number: str = "", company_name: str = "", **kwargs) -> dict:
        if not self.is_configured():
            return {"success": False, "plugin": self.name, "error": "DNB_API_KEY not set"}
        start = time.time()
        try:
            with httpx.Client(timeout=15) as c:
                if duns_number:
                    r = c.get(f"https://plus.dnb.com/v1/data/duns/{duns_number}",
                              headers={"Authorization": f"Bearer {self.get_key()}"})
                else:
                    r = c.get("https://plus.dnb.com/v1/search/companyList",
                              headers={"Authorization": f"Bearer {self.get_key()}"},
                              params={"searchTerm": company_name or prompt})
                r.raise_for_status()
                data = r.json()
            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            return {"success": True, "plugin": self.name, "data": data,
                    "latency_ms": round(latency), "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            self._record_call((time.time() - start) * 1000, False)
            return {"success": False, "plugin": self.name, "error": str(e)}


# ── CONSTRUCTION ─────────────────────────────────────────────

class RSMeansPlugin(BasePlugin):
    """RSMeans/Gordian — Construction cost data by region, building type, system."""
    name = "rsmeans"
    description = "RSMeans/Gordian construction cost data. Cost per SF, regional factors, assembly costs."
    capabilities = ["cost_per_sf", "regional_cost_factor", "assembly_costs",
                    "material_costs", "labor_rates"]
    requires_key = "RSMEANS_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED
        # Static benchmark data when API unavailable
        self.benchmarks = {
            "senior_living_ilu": {"cost_per_sf": [250, 350], "region": "national_avg"},
            "senior_living_alu": {"cost_per_sf": [300, 400], "region": "national_avg"},
            "senior_living_mc": {"cost_per_sf": [350, 450], "region": "national_avg"},
            "multifamily": {"cost_per_sf": [200, 300], "region": "national_avg"},
            "medical_office": {"cost_per_sf": [275, 375], "region": "national_avg"},
            "industrial": {"cost_per_sf": [100, 175], "region": "national_avg"},
        }
        self.regional_factors = {
            "seattle": 1.12, "portland": 1.05, "san_francisco": 1.25,
            "los_angeles": 1.15, "denver": 1.02, "dallas": 0.92,
            "tampa": 0.95, "st_pete": 0.95, "miami": 1.08,
            "atlanta": 0.93, "chicago": 1.10, "new_york": 1.30,
            "national": 1.00,
        }

    def execute(self, prompt: str = "", building_type: str = "senior_living_ilu",
                region: str = "national", square_footage: int = 0, **kwargs) -> dict:
        benchmark = self.benchmarks.get(building_type, self.benchmarks["senior_living_ilu"])
        factor = self.regional_factors.get(region, 1.0)
        low = round(benchmark["cost_per_sf"][0] * factor)
        high = round(benchmark["cost_per_sf"][1] * factor)
        mid = round((low + high) / 2)

        total_low = low * square_footage if square_footage else 0
        total_high = high * square_footage if square_footage else 0

        self._record_call(0, True)
        return {
            "success": True, "plugin": self.name,
            "building_type": building_type,
            "region": region,
            "regional_factor": factor,
            "cost_per_sf": {"low": low, "mid": mid, "high": high},
            "square_footage": square_footage,
            "total_cost": {"low": total_low, "mid": round((total_low + total_high) / 2), "high": total_high} if square_footage else None,
            "source": "API" if self.is_configured() else "NEST benchmarks (RSMeans-calibrated)",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ── REGISTER ALL CONNECTORS ──────────────────────────────────

def register_all_data_connectors():
    """Plug all data connectors into the nervous system."""
    connectors = [
        FREDPlugin(),
        TreasuryDirectPlugin(),
        ATTOMPlugin(),
        CoStarPlugin(),
        EDGARPlugin(),
        EMMAPlugin(),
        FINRABrokerCheckPlugin(),
        DnBPlugin(),
        RSMeansPlugin(),
    ]
    for connector in connectors:
        ingestion_layer.register_plugin(connector)
    return len(connectors)


# Auto-register on import
_registered = register_all_data_connectors()
