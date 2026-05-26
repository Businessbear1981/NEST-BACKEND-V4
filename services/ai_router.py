"""
NEST AI Router — The Power Strip (Hardened)
NEST is the power strip. Every AI tool plugs in via universal API.
One interface. Multiple models. Any new provider = one dict.

Tier 1 (Low):  Universal plugin hub — Claude, Grok, OpenAI, Bloomberg, Moody's, S&P, Meshy, Higgsfield, etc.
Tier 2 (Mid):  NEST modules consume the hub (agents, engines, services)
Tier 3 (High): Backend → Frontend via REST API
"""
import os
import time
import logging
import httpx
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable

log = logging.getLogger("nest.powerstrip")

# ── ENV KEYS ─────────────────────────────────────────────────────
OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_CLAUDE = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
GROK_KEY = os.getenv("GROK_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
BLOOMBERG_KEY = os.getenv("BLOOMBERG_API_KEY", "")
MOODYS_KEY = os.getenv("MOODYS_API_KEY", "")
SP_KEY = os.getenv("SP_GLOBAL_API_KEY", "")
MESHY_KEY = os.getenv("MESHY_API_KEY", "")
HIGGSFIELD_KEY = os.getenv("HIGGSFIELD_API_KEY", "")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
CLAUDE_DIRECT_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FRED_KEY = os.getenv("FRED_API_KEY", "")


# ══════════════════════════════════════════════════════════════════
# PLUGIN INTERFACE
# ══════════════════════════════════════════════════════════════════

@dataclass
class PowerPlugin:
    """Universal plugin definition. One dict = one provider."""
    name: str                          # e.g. "claude", "grok", "bloomberg"
    endpoint: str                      # API URL
    api_key: str                       # resolved key value
    model: str = ""                    # model ID if applicable
    auth_scheme: str = "bearer"        # "bearer" | "x-api-key" | "basic"
    timeout: int = 30                  # seconds
    max_retries: int = 2               # retry count on failure
    retry_delay: float = 1.0           # base delay (exponential backoff)
    priority: int = 10                 # lower = tried first for matched tasks
    task_types: list = field(default_factory=list)  # tasks this plugin handles
    category: str = "ai"              # "ai" | "market_data" | "ratings" | "creative" | "general"
    _healthy: bool = True
    _last_failure: float = 0.0
    _failure_count: int = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def healthy(self) -> bool:
        if not self._healthy and time.time() - self._last_failure > 120:
            # Auto-recover after 2 min cooldown
            self._healthy = True
            self._failure_count = 0
        return self._healthy

    def mark_failure(self):
        self._failure_count += 1
        self._last_failure = time.time()
        if self._failure_count >= 3:
            self._healthy = False
            log.warning(f"Plugin '{self.name}' marked unhealthy after {self._failure_count} failures")

    def mark_success(self):
        self._failure_count = 0
        self._healthy = True


# ══════════════════════════════════════════════════════════════════
# PLUGIN REGISTRY — Add any new API here. One line.
# ══════════════════════════════════════════════════════════════════

PLUGINS: list[PowerPlugin] = [
    # ── PRIMARY: Claude (via OpenRouter) ─────────────────────────
    PowerPlugin(
        name="claude",
        endpoint="https://openrouter.ai/api/v1/chat/completions",
        api_key=OR_KEY,
        model=MODEL_CLAUDE,
        timeout=90,
        max_retries=2,
        priority=1,
        category="ai",
        task_types=[
            "credit_memo", "business_plan", "risk_assessment",
            "feasibility_narrative", "bd_outreach", "investor_teaser",
            "bond_structuring", "executive_summary", "ma_analysis",
            "legal_summary", "general", "fallback",
        ],
    ),

    # ── REAL-TIME: Grok ──────────────────────────────────────────
    PowerPlugin(
        name="grok",
        endpoint="https://api.x.ai/v1/chat/completions",
        api_key=GROK_KEY,
        model="grok-beta",
        timeout=20,
        max_retries=1,
        priority=1,
        category="market_data",
        task_types=[
            "market_rates", "treasury_rates", "market_news",
            "competitor_intel", "real_time_pricing",
        ],
    ),

    # ── FALLBACK: OpenAI ─────────────────────────────────────────
    PowerPlugin(
        name="openai",
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key=OPENAI_KEY,
        model="gpt-4o",
        timeout=30,
        max_retries=1,
        priority=50,
        category="ai",
        task_types=["fallback", "general"],
    ),

    # ── MARKET DATA: Bloomberg ───────────────────────────────────
    PowerPlugin(
        name="bloomberg",
        endpoint="https://api.bloomberg.com/v1/data",
        api_key=BLOOMBERG_KEY,
        auth_scheme="x-api-key",
        timeout=15,
        priority=1,
        category="market_data",
        task_types=[
            "bond_pricing", "live_mtm", "yield_curve",
            "spread_data", "index_data",
        ],
    ),

    # ── RATINGS: Moody's Analytics ───────────────────────────────
    PowerPlugin(
        name="moodys",
        endpoint="https://api.moodysanalytics.com/v1",
        api_key=MOODYS_KEY,
        auth_scheme="x-api-key",
        timeout=20,
        priority=1,
        category="ratings",
        task_types=["credit_rating", "default_probability", "lgd_estimate"],
    ),

    # ── RATINGS: S&P Global ──────────────────────────────────────
    PowerPlugin(
        name="sp_global",
        endpoint="https://api.spglobal.com/v1",
        api_key=SP_KEY,
        auth_scheme="x-api-key",
        timeout=20,
        priority=2,
        category="ratings",
        task_types=["credit_rating", "sector_outlook", "industry_benchmark"],
    ),

    # ── CREATIVE: Meshy (3D generation) ──────────────────────────
    PowerPlugin(
        name="meshy",
        endpoint="https://api.meshy.ai/v2",
        api_key=MESHY_KEY,
        timeout=60,
        priority=1,
        category="creative",
        task_types=["3d_model", "texture_generation"],
    ),

    # ── CREATIVE: Higgsfield (video/image) ───────────────────────
    PowerPlugin(
        name="higgsfield",
        endpoint="https://api.higgsfield.ai/v1",
        api_key=HIGGSFIELD_KEY,
        timeout=60,
        priority=1,
        category="creative",
        task_types=["video_generation", "image_generation"],
    ),

    # ── AI: DeepSeek (cost-efficient reasoning) ──────────────────
    PowerPlugin(
        name="deepseek",
        endpoint="https://api.deepseek.com/chat/completions",
        api_key=DEEPSEEK_KEY,
        model="deepseek-chat",
        timeout=45,
        max_retries=1,
        priority=5,
        category="ai",
        task_types=["general", "code_analysis", "data_extraction", "fallback"],
    ),

    # ── AI: Claude Direct (Anthropic API, no OpenRouter) ─────────
    PowerPlugin(
        name="claude_direct",
        endpoint="https://api.anthropic.com/v1/messages",
        api_key=CLAUDE_DIRECT_KEY,
        model="claude-sonnet-4-20250514",
        auth_scheme="x-api-key",
        timeout=90,
        max_retries=2,
        priority=2,
        category="ai",
        task_types=[
            "credit_memo", "business_plan", "risk_assessment",
            "bond_structuring", "executive_summary", "ma_analysis",
            "general", "fallback",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════
# PLUGIN HUB — The Engine
# ══════════════════════════════════════════════════════════════════

class PluginHub:
    """
    Universal plugin router with retry, fallback, and health tracking.
    Any NEST module calls hub.route(task_type, prompt) — the hub picks
    the best available plugin, retries on failure, falls through to
    the next plugin in priority order.
    """

    def __init__(self, plugins: list[PowerPlugin] = None):
        self._plugins = plugins or PLUGINS

    # ── Core routing ─────────────────────────────────────────────

    def route(self, task_type: str, prompt: str,
              system: str = None, force_tool: str = None) -> dict:
        """Route a task to the best available plugin."""
        if force_tool:
            plugin = self._get_plugin(force_tool)
            if plugin and plugin.configured:
                return self._call_plugin(plugin, prompt, system)

        # Find plugins that handle this task type, sorted by priority
        candidates = self._candidates_for(task_type)
        if not candidates:
            # Fall back to Claude for anything unmapped
            candidates = [p for p in self._plugins if p.name == "claude" and p.configured]

        for plugin in candidates:
            result = self._call_plugin(plugin, prompt, system)
            if result["success"]:
                return result
            log.info(f"Plugin '{plugin.name}' failed for '{task_type}', trying next...")

        return {"tool": "none", "content": "", "success": False,
                "error": "All plugins failed", "timestamp": _ts()}

    def call_direct(self, plugin_name: str, prompt: str,
                    system: str = None) -> dict:
        """Call a specific plugin by name — no fallback chain."""
        plugin = self._get_plugin(plugin_name)
        if not plugin:
            return {"tool": plugin_name, "content": "", "success": False,
                    "error": f"Plugin '{plugin_name}' not registered", "timestamp": _ts()}
        if not plugin.configured:
            return {"tool": plugin_name, "content": "", "success": False,
                    "error": f"Plugin '{plugin_name}' not configured (missing API key)", "timestamp": _ts()}
        return self._call_plugin(plugin, prompt, system)

    # ── Market rates (Grok → FRED → static) ──────────────────────

    def get_market_rates(self) -> dict:
        """Live rates — Grok first, FRED fallback, static last."""
        grok = self._get_plugin("grok")
        if grok and grok.configured and grok.healthy:
            r = self._call_plugin(
                grok,
                "Current US market data: 10yr Treasury rate, SOFR, "
                "IG credit spread bps, senior living cap rate range. "
                "Be specific with today's numbers.",
            )
            if r["success"]:
                return {"source": "grok", "data": r["content"],
                        "timestamp": r["timestamp"]}

        # FRED fallback
        try:
            with httpx.Client(timeout=8) as c:
                r = c.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={"series_id": "DGS10", "api_key": FRED_KEY,
                            "sort_order": "desc", "limit": 1, "file_type": "json"})
                if r.status_code == 200:
                    obs = r.json().get("observations", [])
                    rate = float(obs[0]["value"]) if obs else 4.28
                    return {"source": "FRED", "treasury_10yr_pct": rate,
                            "sofr_pct": 5.33, "ig_spread_bps": 112,
                            "timestamp": _ts()}
        except Exception:
            pass

        return {"source": "static_fallback", "treasury_10yr_pct": 4.28,
                "sofr_pct": 5.33, "ig_spread_bps": 112}

    # ── Bond pricing via power strip ─────────────────────────────

    def get_bond_pricing(self, bond_params: dict) -> dict:
        """
        Route bond pricing to Bloomberg if configured, otherwise
        use internal pricing engine + Grok for spread context.
        """
        bloomberg = self._get_plugin("bloomberg")
        if bloomberg and bloomberg.configured and bloomberg.healthy:
            r = self._call_plugin(
                bloomberg,
                f"Price bond: {bond_params}",
            )
            if r["success"]:
                return {"source": "bloomberg", "data": r["content"],
                        "timestamp": r["timestamp"]}

        # Fallback: internal engine + AI context
        from engines.pricing import price_bond
        try:
            internal = price_bond(
                par=bond_params.get("par", 100_000_000),
                clean_price=bond_params.get("clean_price", 100),
                coupon_rate=bond_params.get("coupon_rate", 0.065),
                ytm=bond_params.get("ytm", 0.07),
                maturity_years=bond_params.get("maturity_years", 10),
                rating=bond_params.get("rating", "BBB"),
            )
            return {"source": "nest_engine", "data": internal,
                    "timestamp": _ts()}
        except Exception as e:
            return {"source": "error", "data": None,
                    "error": str(e), "timestamp": _ts()}

    # ── Refi signal detection ────────────────────────────────────

    def get_refi_signals(self, deal: dict) -> dict:
        """
        Check if current market conditions trigger a call/refi opportunity.
        Uses Grok for live rates → CreditEngine for call/put analysis.
        """
        rates = self.get_market_rates()
        from services.core import CreditEngine
        engine = CreditEngine()

        treasury_bps = int(rates.get("treasury_10yr_pct", 4.28) * 100)
        orig_rate = int(deal.get("original_rate_pct", 7.0) * 100)

        analysis = engine.call_put_analysis(treasury_bps, orig_rate, deal)
        analysis["market_rates"] = rates
        analysis["timestamp"] = _ts()
        return analysis

    # ── Status / health ──────────────────────────────────────────

    def get_tool_status(self) -> dict:
        """Full status of every registered plugin."""
        status = {}
        for p in self._plugins:
            status[p.name] = {
                "configured": p.configured,
                "healthy": p.healthy,
                "model": p.model or None,
                "category": p.category,
                "task_types": p.task_types,
                "priority": p.priority,
                "primary": p.priority == 1,
                "failure_count": p._failure_count,
            }
        configured_count = sum(1 for p in self._plugins if p.configured)
        return {
            "tools": status,
            "total_plugins": len(self._plugins),
            "configured_plugins": configured_count,
            "primary": "claude",
            "nest_is_power_strip": True,
            "philosophy": (
                "NEST IS THE POWER STRIP. Every AI tool, data feed, and "
                "rating agency plugs in via universal API. Claude is primary. "
                "Grok adds real-time data. Bloomberg for pricing. Moody's/S&P "
                "for ratings. System works even with only Claude configured."
            ),
        }

    def list_plugins(self) -> list[dict]:
        """Quick list of all registered plugins."""
        return [
            {"name": p.name, "configured": p.configured, "healthy": p.healthy,
             "category": p.category, "priority": p.priority}
            for p in self._plugins
        ]

    # ── Plugin management ────────────────────────────────────────

    def register(self, plugin: PowerPlugin):
        """Register a new plugin at runtime. One line."""
        self._plugins.append(plugin)
        self._plugins.sort(key=lambda p: p.priority)
        log.info(f"Plugin '{plugin.name}' registered (priority={plugin.priority})")

    # ── Internal ─────────────────────────────────────────────────

    def _get_plugin(self, name: str) -> Optional[PowerPlugin]:
        return next((p for p in self._plugins if p.name == name), None)

    def _candidates_for(self, task_type: str) -> list[PowerPlugin]:
        """Plugins that handle this task, configured + healthy, sorted by priority."""
        return sorted(
            [p for p in self._plugins
             if task_type in p.task_types and p.configured and p.healthy],
            key=lambda p: p.priority,
        )

    def _call_plugin(self, plugin: PowerPlugin, prompt: str,
                     system: str = None) -> dict:
        """Call a plugin with retry + exponential backoff."""
        last_error = ""
        for attempt in range(plugin.max_retries + 1):
            try:
                result = self._execute(plugin, prompt, system)
                plugin.mark_success()
                return result
            except Exception as e:
                last_error = str(e)
                plugin.mark_failure()
                if attempt < plugin.max_retries:
                    delay = plugin.retry_delay * (2 ** attempt)
                    log.info(f"Plugin '{plugin.name}' attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)

        return {"tool": plugin.name, "content": "", "success": False,
                "error": last_error, "timestamp": _ts()}

    def _execute(self, plugin: PowerPlugin, prompt: str,
                 system: str = None) -> dict:
        """Execute a single API call to a plugin."""
        # Claude via OpenRouter — system prompt + referer headers
        if plugin.name == "claude":
            return self._call_claude(plugin, prompt, system)

        # Claude Direct — Anthropic Messages API (different format)
        if plugin.name == "claude_direct":
            return self._call_claude_direct(plugin, prompt, system)

        # Standard OpenAI-compatible chat API (Grok, OpenAI, DeepSeek, etc.)
        if plugin.category == "ai" or plugin.name in ("grok", "openai", "deepseek"):
            return self._call_chat(plugin, prompt, system)

        # Market data / ratings — POST with JSON body
        return self._call_rest(plugin, prompt)

    def _call_claude(self, plugin: PowerPlugin, prompt: str,
                     system: str = None) -> dict:
        from services.core import JIMMY_LEE
        msgs = [
            {"role": "system", "content": system or JIMMY_LEE},
            {"role": "user", "content": prompt},
        ]
        with httpx.Client(timeout=plugin.timeout) as c:
            r = c.post(
                plugin.endpoint,
                headers={
                    "Authorization": f"Bearer {plugin.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://www.ardanedgecapital.com",
                    "X-Title": "NEST Capital Partners",
                },
                json={"model": plugin.model, "max_tokens": 4096, "messages": msgs},
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return {"tool": "claude", "model": plugin.model,
                    "content": content, "success": True, "timestamp": _ts()}

    def _call_claude_direct(self, plugin: PowerPlugin, prompt: str,
                            system: str = None) -> dict:
        """Anthropic Messages API — different from OpenAI-compatible format."""
        from services.core import JIMMY_LEE
        body = {
            "model": plugin.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system or JIMMY_LEE:
            body["system"] = system or JIMMY_LEE

        with httpx.Client(timeout=plugin.timeout) as c:
            r = c.post(
                plugin.endpoint,
                headers={
                    "x-api-key": plugin.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            r.raise_for_status()
            content = r.json()["content"][0]["text"]
            return {"tool": "claude_direct", "model": plugin.model,
                    "content": content, "success": True, "timestamp": _ts()}

    def _call_chat(self, plugin: PowerPlugin, prompt: str,
                   system: str = None) -> dict:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if plugin.auth_scheme == "bearer":
            headers["Authorization"] = f"Bearer {plugin.api_key}"
        elif plugin.auth_scheme == "x-api-key":
            headers["X-Api-Key"] = plugin.api_key

        with httpx.Client(timeout=plugin.timeout) as c:
            r = c.post(
                plugin.endpoint,
                headers=headers,
                json={"model": plugin.model, "max_tokens": 1000, "messages": msgs},
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return {"tool": plugin.name, "model": plugin.model,
                    "content": content, "success": True, "timestamp": _ts()}

    def _call_rest(self, plugin: PowerPlugin, payload: str) -> dict:
        headers = {"Content-Type": "application/json"}
        if plugin.auth_scheme == "bearer":
            headers["Authorization"] = f"Bearer {plugin.api_key}"
        elif plugin.auth_scheme == "x-api-key":
            headers["X-Api-Key"] = plugin.api_key

        with httpx.Client(timeout=plugin.timeout) as c:
            r = c.post(
                plugin.endpoint,
                headers=headers,
                json={"query": payload},
            )
            r.raise_for_status()
            data = r.json()
            return {"tool": plugin.name, "content": data,
                    "success": True, "timestamp": _ts()}


# ── Utility ──────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.utcnow().isoformat()


# ══════════════════════════════════════════════════════════════════
# BACKWARD-COMPATIBLE WRAPPER
# The old AIRouter interface still works. Existing code doesn't break.
# ══════════════════════════════════════════════════════════════════

class AIRouter:
    """Legacy wrapper — delegates everything to PluginHub."""

    def __init__(self):
        self.hub = PluginHub()

    def route(self, task_type: str, prompt: str,
              system: str = None, force_tool: str = None) -> dict:
        return self.hub.route(task_type, prompt, system, force_tool)

    def get_market_rates(self) -> dict:
        return self.hub.get_market_rates()

    def get_tool_status(self) -> dict:
        return self.hub.get_tool_status()


# ── SINGLETONS (import these) ────────────────────────────────────
plugin_hub = PluginHub()
ai_router = AIRouter()
