"""
NEST Ingestion Plugin Layer — Central Nervous System.
Layer 1 of the two-layer backend architecture.

Every external AI service plugs in through a standardized interface.
Each plugin: connect → health check → execute → normalize response.
The ingestion layer handles auth, retries, fallback, and telemetry.

Plugins:
  Claude   — Primary intelligence. Analysis, writing, modeling, structuring.
  ChatGPT  — Fallback content generation. Second opinion engine.
  Grammarly — Document quality. Proofreading, tone, compliance language.
  Higgsfield — AI video generation. Marketing, investor presentations, brand content.

NEST Advisors is the power strip. These are the plugs.
"""
import os
import time
import hashlib
import json
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List


# ── PLUGIN REGISTRY ──────────────────────────────────────────

class PluginStatus:
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class BasePlugin:
    """Every plugin implements this interface."""

    name: str = "base"
    description: str = ""
    capabilities: list = []
    requires_key: str = ""

    def __init__(self):
        self.status = PluginStatus.DISCONNECTED
        self.last_call = None
        self.call_count = 0
        self.error_count = 0
        self.total_tokens = 0
        self.avg_latency_ms = 0
        self._latencies: list = []

    def get_key(self) -> str:
        return os.getenv(self.requires_key, "")

    def is_configured(self) -> bool:
        return bool(self.get_key())

    def health_check(self) -> dict:
        return {
            "plugin": self.name,
            "status": self.status,
            "configured": self.is_configured(),
            "calls": self.call_count,
            "errors": self.error_count,
            "avg_latency_ms": round(self.avg_latency_ms),
            "last_call": self.last_call,
        }

    def _record_call(self, latency_ms: float, success: bool, tokens: int = 0):
        self.call_count += 1
        self.last_call = datetime.utcnow().isoformat()
        self.total_tokens += tokens
        if not success:
            self.error_count += 1
        self._latencies.append(latency_ms)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-50:]
        self.avg_latency_ms = sum(self._latencies) / len(self._latencies)

    def execute(self, prompt: str, **kwargs) -> dict:
        raise NotImplementedError


# ── CLAUDE PLUGIN ────────────────────────────────────────────

class ClaudePlugin(BasePlugin):
    name = "claude"
    description = "Primary intelligence engine. Analysis, writing, bond structuring, credit memos, M&A modeling."
    capabilities = [
        "credit_memo", "business_plan", "risk_assessment", "feasibility_narrative",
        "bd_outreach", "investor_teaser", "bond_structuring", "executive_summary",
        "ma_analysis", "legal_summary", "financial_modeling", "compliance_review",
        "audit_report", "rating_presentation", "bank_presentation",
    ]
    requires_key = "OPENROUTER_API_KEY"

    def __init__(self):
        super().__init__()
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str, system: str = None, max_tokens: int = None) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "OPENROUTER_API_KEY not set", "plugin": self.name}

        start = time.time()
        try:
            key = self.get_key()
            with httpx.Client(timeout=60) as c:
                r = c.post("https://openrouter.ai/api/v1/chat/completions",
                           headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                           json={
                               "model": f"anthropic/{self.model}",
                               "max_tokens": max_tokens or self.max_tokens,
                               "messages": [
                                   *([{"role": "system", "content": system}] if system else []),
                                   {"role": "user", "content": prompt},
                               ],
                           })
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)

            latency = (time.time() - start) * 1000
            self._record_call(latency, True, tokens)
            self.status = PluginStatus.CONNECTED

            return {
                "success": True,
                "plugin": self.name,
                "model": self.model,
                "content": content,
                "tokens": tokens,
                "latency_ms": round(latency),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except httpx.HTTPStatusError as e:
            latency = (time.time() - start) * 1000
            self._record_call(latency, False)
            if e.response.status_code == 429:
                self.status = PluginStatus.RATE_LIMITED
            else:
                self.status = PluginStatus.ERROR
            return {"success": False, "plugin": self.name, "error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            latency = (time.time() - start) * 1000
            self._record_call(latency, False)
            self.status = PluginStatus.ERROR
            return {"success": False, "plugin": self.name, "error": str(e)}


# ── CHATGPT PLUGIN ───────────────────────────────────────────

class ChatGPTPlugin(BasePlugin):
    name = "chatgpt"
    description = "Fallback content engine. Second opinion. Alternative drafts. General knowledge."
    capabilities = [
        "fallback_content", "second_opinion", "general_research",
        "content_drafting", "email_drafting", "market_summary",
    ]
    requires_key = "OPENAI_API_KEY"

    def __init__(self):
        super().__init__()
        self.model = "gpt-4o"
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str, system: str = None, max_tokens: int = 2000) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "OPENAI_API_KEY not set", "plugin": self.name}

        start = time.time()
        try:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})

            with httpx.Client(timeout=30) as c:
                r = c.post("https://api.openai.com/v1/chat/completions",
                           headers={"Authorization": f"Bearer {self.get_key()}", "Content-Type": "application/json"},
                           json={"model": self.model, "max_tokens": max_tokens, "messages": msgs})
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)

            latency = (time.time() - start) * 1000
            self._record_call(latency, True, tokens)
            self.status = PluginStatus.CONNECTED

            return {
                "success": True,
                "plugin": self.name,
                "model": self.model,
                "content": content,
                "tokens": tokens,
                "latency_ms": round(latency),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            self._record_call(latency, False)
            self.status = PluginStatus.ERROR
            return {"success": False, "plugin": self.name, "error": str(e)}


# ── GRAMMARLY PLUGIN ─────────────────────────────────────────

class GrammarlyPlugin(BasePlugin):
    name = "grammarly"
    description = "Document quality engine. Proofreading, tone consistency, compliance language, FINRA-safe wording."
    capabilities = [
        "proofread", "tone_check", "compliance_language",
        "finra_safe_wording", "document_polish", "readability_score",
    ]
    requires_key = "GRAMMARLY_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str, document_text: str = "", check_type: str = "full") -> dict:
        if not self.is_configured():
            # Grammarly not configured — use Claude as fallback proofreader
            return self._claude_fallback(prompt, document_text, check_type)

        start = time.time()
        try:
            with httpx.Client(timeout=20) as c:
                r = c.post("https://api.grammarly.com/v1/check",
                           headers={"Authorization": f"Bearer {self.get_key()}", "Content-Type": "application/json"},
                           json={"text": document_text or prompt, "checks": [check_type]})
                r.raise_for_status()
                data = r.json()

            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            self.status = PluginStatus.CONNECTED

            return {
                "success": True,
                "plugin": self.name,
                "corrections": data.get("corrections", []),
                "score": data.get("score", 0),
                "tone": data.get("tone", ""),
                "latency_ms": round(latency),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            self._record_call(latency, False)
            self.status = PluginStatus.ERROR
            return self._claude_fallback(prompt, document_text, check_type)

    def _claude_fallback(self, prompt: str, document_text: str, check_type: str) -> dict:
        """When Grammarly unavailable, Claude handles proofreading."""
        claude = ingestion_layer.plugins.get("claude")
        if not claude:
            return {"success": False, "plugin": self.name, "error": "No fallback available"}

        proofread_prompt = f"""Proofread and improve this document. Check for:
- Grammar and spelling errors
- Tone consistency (institutional, Jimmy Lee voice)
- FINRA-compliant language (no guarantees, no misleading claims)
- Readability for credit officers and rating agencies

Return: corrected text + list of changes made + readability score (1-100).

DOCUMENT:
{document_text or prompt}"""

        result = claude.execute(proofread_prompt)
        if result["success"]:
            result["plugin"] = f"{self.name}_via_claude"
            result["fallback"] = True
        return result


# ── HIGGSFIELD PLUGIN ────────────────────────────────────────

class HiggsFieldPlugin(BasePlugin):
    name = "higgsfield"
    description = "AI video generation. Marketing videos, investor presentations, brand content, property showcases."
    capabilities = [
        "marketing_video", "investor_presentation_video", "property_showcase",
        "brand_content", "social_media_clip", "explainer_video",
    ]
    requires_key = "HIGGSFIELD_API_KEY"

    def __init__(self):
        super().__init__()
        self.status = PluginStatus.CONNECTED if self.is_configured() else PluginStatus.DISCONNECTED

    def execute(self, prompt: str, video_type: str = "marketing",
                duration_seconds: int = 30, aspect_ratio: str = "16:9",
                style: str = "cinematic") -> dict:
        if not self.is_configured():
            return {"success": False, "error": "HIGGSFIELD_API_KEY not set", "plugin": self.name}

        start = time.time()
        try:
            with httpx.Client(timeout=120) as c:
                r = c.post("https://api.higgsfield.ai/v1/videos/generate",
                           headers={"Authorization": f"Bearer {self.get_key()}", "Content-Type": "application/json"},
                           json={
                               "prompt": prompt,
                               "type": video_type,
                               "duration": duration_seconds,
                               "aspect_ratio": aspect_ratio,
                               "style": style,
                           })
                r.raise_for_status()
                data = r.json()

            latency = (time.time() - start) * 1000
            self._record_call(latency, True)
            self.status = PluginStatus.CONNECTED

            return {
                "success": True,
                "plugin": self.name,
                "video_id": data.get("id", ""),
                "video_url": data.get("url", ""),
                "status": data.get("status", "processing"),
                "duration_seconds": duration_seconds,
                "latency_ms": round(latency),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            self._record_call(latency, False)
            self.status = PluginStatus.ERROR
            return {"success": False, "plugin": self.name, "error": str(e)}

    def check_video_status(self, video_id: str) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "Not configured"}
        try:
            with httpx.Client(timeout=10) as c:
                r = c.get(f"https://api.higgsfield.ai/v1/videos/{video_id}",
                          headers={"Authorization": f"Bearer {self.get_key()}"})
                r.raise_for_status()
                return {"success": True, **r.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── INGESTION LAYER ──────────────────────────────────────────

TASK_ROUTING = {
    # Claude — primary intelligence
    "credit_memo": "claude",
    "business_plan": "claude",
    "risk_assessment": "claude",
    "feasibility_narrative": "claude",
    "bd_outreach": "claude",
    "investor_teaser": "claude",
    "bond_structuring": "claude",
    "executive_summary": "claude",
    "ma_analysis": "claude",
    "legal_summary": "claude",
    "financial_modeling": "claude",
    "compliance_review": "claude",
    "audit_report": "claude",
    "rating_presentation": "claude",
    "bank_presentation": "claude",
    # ChatGPT — fallback + second opinion
    "second_opinion": "chatgpt",
    "general_research": "chatgpt",
    "content_drafting": "chatgpt",
    "email_drafting": "chatgpt",
    "market_summary": "chatgpt",
    # Grammarly — document quality
    "proofread": "grammarly",
    "tone_check": "grammarly",
    "compliance_language": "grammarly",
    "document_polish": "grammarly",
    # Higgsfield — video generation
    "marketing_video": "higgsfield",
    "investor_presentation_video": "higgsfield",
    "property_showcase": "higgsfield",
    "brand_content": "higgsfield",
    "social_media_clip": "higgsfield",
}


class IngestionLayer:
    """
    Central nervous system. Routes tasks to plugins.
    Handles fallback chains, telemetry, and response normalization.
    """

    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {
            "claude": ClaudePlugin(),
            "chatgpt": ChatGPTPlugin(),
            "grammarly": GrammarlyPlugin(),
            "higgsfield": HiggsFieldPlugin(),
        }
        self.call_log: List[dict] = []

    def ingest(self, task_type: str, prompt: str,
               force_plugin: str = None, **kwargs) -> dict:
        """
        Main entry point. Send any task — the nervous system routes it.
        Returns normalized response regardless of which plugin handled it.
        """
        plugin_name = force_plugin or TASK_ROUTING.get(task_type, "claude")
        plugin = self.plugins.get(plugin_name)

        if not plugin:
            return {"success": False, "error": f"Unknown plugin: {plugin_name}"}

        if not plugin.is_configured():
            # Fallback chain: try claude, then chatgpt
            for fallback_name in ["claude", "chatgpt"]:
                fallback = self.plugins.get(fallback_name)
                if fallback and fallback.is_configured() and fallback_name != plugin_name:
                    result = fallback.execute(prompt, **kwargs)
                    result["original_plugin"] = plugin_name
                    result["fallback_used"] = fallback_name
                    self._log(task_type, plugin_name, fallback_name, result)
                    return result
            return {"success": False, "error": f"Plugin '{plugin_name}' not configured and no fallback available"}

        result = plugin.execute(prompt, **kwargs)
        self._log(task_type, plugin_name, None, result)

        # If primary failed, try fallback
        if not result.get("success") and plugin_name != "claude":
            claude = self.plugins.get("claude")
            if claude and claude.is_configured():
                result = claude.execute(prompt, **kwargs)
                result["original_plugin"] = plugin_name
                result["fallback_used"] = "claude"
                self._log(task_type, plugin_name, "claude", result)

        return result

    def _log(self, task_type: str, plugin: str, fallback: str, result: dict):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_type": task_type,
            "plugin": plugin,
            "fallback": fallback,
            "success": result.get("success", False),
            "latency_ms": result.get("latency_ms", 0),
            "tokens": result.get("tokens", 0),
        }
        self.call_log.append(entry)
        if len(self.call_log) > 1000:
            self.call_log = self.call_log[-500:]

    def get_dashboard(self) -> dict:
        """Full nervous system status."""
        plugins_status = {}
        for name, plugin in self.plugins.items():
            health = plugin.health_check()
            health["capabilities"] = plugin.capabilities
            health["description"] = plugin.description
            plugins_status[name] = health

        total_calls = sum(p.call_count for p in self.plugins.values())
        total_errors = sum(p.error_count for p in self.plugins.values())
        connected = sum(1 for p in self.plugins.values() if p.status == PluginStatus.CONNECTED)

        return {
            "nervous_system": "NEST Advisors Ingestion Layer",
            "plugins_total": len(self.plugins),
            "plugins_connected": connected,
            "plugins_disconnected": len(self.plugins) - connected,
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate_pct": round(total_errors / total_calls * 100, 1) if total_calls else 0,
            "plugins": plugins_status,
            "task_routing": TASK_ROUTING,
            "recent_calls": self.call_log[-20:],
        }

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        return self.plugins.get(name)

    def register_plugin(self, plugin: BasePlugin):
        """Hot-plug a new service into the nervous system."""
        self.plugins[plugin.name] = plugin

    def multi_ingest(self, task_type: str, prompt: str,
                     plugins: List[str] = None) -> dict:
        """
        Fan-out: send same prompt to multiple plugins simultaneously.
        Used for second opinions, A/B content testing, consensus building.
        """
        targets = plugins or ["claude", "chatgpt"]
        results = {}
        for name in targets:
            plugin = self.plugins.get(name)
            if plugin and plugin.is_configured():
                results[name] = plugin.execute(prompt)
            else:
                results[name] = {"success": False, "error": f"{name} not configured"}

        # Pick best result (prefer success, then by plugin priority)
        priority = ["claude", "chatgpt", "grammarly", "higgsfield"]
        best = None
        for p in priority:
            if p in results and results[p].get("success"):
                best = p
                break

        return {
            "task_type": task_type,
            "fan_out_count": len(targets),
            "results": results,
            "best_result": best,
            "best_content": results.get(best, {}).get("content", "") if best else "",
            "consensus": len([r for r in results.values() if r.get("success")]),
        }


# ── SINGLETON ────────────────────────────────────────────────

ingestion_layer = IngestionLayer()
