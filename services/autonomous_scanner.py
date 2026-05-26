"""
Autonomous Scanner — The Intelligence Loop.

Runs on a schedule. Pulls signals from real sources (EDGAR, FRED, Chrome).
Feeds them into the Convergence Engine. Has Claude analyze findings.
Surfaces HEAT events without any human input.

This is the brain that never sleeps.
"""

from __future__ import annotations

import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Any

import httpx


ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
FRED_KEY = os.environ.get("FRED_API_KEY", "")
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL_SECONDS", "3600"))  # default 1 hour


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _claude(prompt: str, max_tokens: int = 1000) -> str:
    """Call Claude API directly. Returns text response."""
    if not ANTHROPIC_KEY:
        return "[Claude API key not configured]"
    try:
        with httpx.Client(timeout=30) as c:
            r = c.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]
    except Exception as e:
        return f"[Claude error: {e}]"


class AutonomousScanner:
    """
    The brain that never sleeps.

    Pulls signals from real sources, runs Claude analysis,
    feeds results into the convergence engine.
    """

    def __init__(self, convergence_engine: Any = None) -> None:
        self._convergence = convergence_engine
        self._scan_log: list[dict[str, Any]] = []
        self._findings: list[dict[str, Any]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_scan: str | None = None

    # ── Start / Stop ──────────────────────────────────────────

    def start(self) -> dict[str, Any]:
        """Start the autonomous scan loop in a background thread."""
        if self._running:
            return {"status": "already_running", "last_scan": self._last_scan}

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        # Run first scan immediately
        self._log("SCANNER ONLINE", "Autonomous intelligence loop started")
        return {"status": "started", "interval_seconds": SCAN_INTERVAL}

    def stop(self) -> dict[str, Any]:
        """Stop the scan loop."""
        self._running = False
        self._log("SCANNER OFFLINE", "Loop stopped")
        return {"status": "stopped"}

    def _loop(self) -> None:
        """Main loop — runs scans at interval."""
        while self._running:
            try:
                self.run_scan()
            except Exception as e:
                self._log("SCAN ERROR", str(e))
            time.sleep(SCAN_INTERVAL)

    # ── Manual Scan ───────────────────────────────────────────

    def run_scan(self) -> dict[str, Any]:
        """Run a single intelligence scan cycle. Can be called manually or by the loop."""
        self._log("SCAN STARTED", "Beginning intelligence cycle")
        results = {
            "timestamp": _now(),
            "sources_scanned": [],
            "signals_found": 0,
            "findings": [],
        }

        # 1. Pull FRED rates
        fred_signals = self._scan_fred()
        results["sources_scanned"].append("FRED")
        results["signals_found"] += len(fred_signals)

        # 2. Pull EDGAR filings
        edgar_signals = self._scan_edgar()
        results["sources_scanned"].append("SEC EDGAR")
        results["signals_found"] += len(edgar_signals)

        # 3. Have Claude analyze what we found
        if fred_signals or edgar_signals:
            analysis = self._claude_analyze(fred_signals, edgar_signals)
            results["findings"].append(analysis)
            self._findings.append(analysis)

        # 4. Feed new signals into convergence engine
        if self._convergence and edgar_signals:
            for sig in edgar_signals:
                self._convergence._signals.append(sig)
            self._convergence._scan_for_convergence()
            new_heat = len(self._convergence._heat_events)
            results["heat_events_after_scan"] = new_heat

        self._last_scan = _now()
        self._log("SCAN COMPLETE", f"{results['signals_found']} signals, {len(results['findings'])} findings")
        return results

    # ── Source Scanners ───────────────────────────────────────

    def _scan_fred(self) -> list[dict[str, Any]]:
        """Pull latest treasury rates from FRED. Returns signals if rates moved significantly."""
        if not FRED_KEY:
            self._log("FRED SKIP", "No API key")
            return []

        signals = []
        series = {"DGS10": "10yr Treasury", "DGS5": "5yr Treasury", "SOFR": "SOFR"}

        try:
            with httpx.Client(timeout=10) as c:
                for series_id, label in series.items():
                    r = c.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            "series_id": series_id,
                            "api_key": FRED_KEY,
                            "sort_order": "desc",
                            "limit": 2,
                            "file_type": "json",
                        },
                    )
                    r.raise_for_status()
                    obs = r.json().get("observations", [])
                    if len(obs) >= 2:
                        current = float(obs[0]["value"]) if obs[0]["value"] != "." else None
                        prev = float(obs[1]["value"]) if obs[1]["value"] != "." else None
                        if current is not None and prev is not None:
                            delta_bps = round((current - prev) * 100, 1)
                            if abs(delta_bps) >= 3:  # 3bps move = noteworthy
                                signals.append({
                                    "id": f"fred-{series_id}-{obs[0]['date']}",
                                    "type": "rate_movement",
                                    "entity": f"US {label}",
                                    "location": "US Market",
                                    "date": _now(),
                                    "details": f"{label}: {current}% (was {prev}%, delta {delta_bps:+}bps)",
                                    "state": "US",
                                    "source": "FRED",
                                    "data": {"current": current, "previous": prev, "delta_bps": delta_bps},
                                })

            self._log("FRED SCANNED", f"{len(signals)} rate signals")
        except Exception as e:
            self._log("FRED ERROR", str(e))

        return signals

    def _scan_edgar(self) -> list[dict[str, Any]]:
        """Pull recent SEC EDGAR filings. Looks for Form D (equity raises), 8-K (material events), SC 13D (ownership changes)."""
        signals = []
        forms = ["D", "8-K", "SC 13D"]

        try:
            with httpx.Client(timeout=15) as c:
                for form_type in forms:
                    r = c.get(
                        "https://efts.sec.gov/LATEST/search-index",
                        params={
                            "q": f'root_forms:"{form_type}"',
                            "from": "0",
                            "size": "5",
                        },
                        headers={"User-Agent": "NEST Advisors research@nestadvisors.ai"},
                    )

                    if r.status_code == 200:
                        data = r.json()
                        hits = data.get("hits", {}).get("hits", [])
                        for hit in hits[:5]:
                            source = hit.get("_source", {})
                            names = source.get("display_names", [])
                            entity_name = names[0].split("(CIK")[0].strip() if names else "Unknown"
                            state = source.get("biz_state", source.get("state_of_incorp", ""))

                            signal_type = {
                                "D": "equity_raise",
                                "8-K": "8k_filing",
                                "SC 13D": "sc13d_filing",
                            }.get(form_type, "sec_filing")

                            signals.append({
                                "id": f"edgar-{form_type.replace(' ', '')}-{hit.get('_id', '')}",
                                "type": signal_type,
                                "entity": str(entity_name),
                                "location": f"{state}, US" if state else "US",
                                "date": _now(),
                                "details": f"SEC {form_type} filed by {entity_name}" + (f" in {state}" if state else ""),
                                "state": state or "US",
                                "source": "SEC EDGAR",
                                "data": {"form_type": form_type, "filing_id": hit.get("_id", "")},
                            })

            self._log("EDGAR SCANNED", f"{len(signals)} filings found ({', '.join(forms)})")
        except Exception as e:
            self._log("EDGAR ERROR", str(e))

        return signals

    # ── Claude Analysis ───────────────────────────────────────

    def _claude_analyze(self, fred_signals: list, edgar_signals: list) -> dict[str, Any]:
        """Have Claude analyze the scan results and identify opportunities."""
        prompt = f"""You are the intelligence analyst for NEST Advisors, a digital investment bank focused on bond structuring, M&A, and distressed CRE acquisition.

I just scanned market data and SEC filings. Here's what I found:

MARKET SIGNALS (FRED):
{json.dumps(fred_signals, indent=2) if fred_signals else "No significant rate movements."}

SEC FILINGS (last 7 days):
{json.dumps([{{"entity": s["entity"], "type": s["type"], "details": s["details"], "state": s["state"]}} for s in edgar_signals], indent=2) if edgar_signals else "No new filings found."}

Analyze these signals. For each interesting finding:
1. What is happening?
2. Is this a potential deal opportunity for NEST (bond, M&A, Phoenix distressed, term lending)?
3. What agent should we deploy (Merlin for M&A scoring, Maxwell for credit analysis, Sentinel for risk, LenderScout for financing, Sterling for placement)?
4. Urgency: critical / high / medium / low

Be direct. Lead with conclusions. No hedging. If nothing interesting, say so in one sentence."""

        analysis_text = _claude(prompt, max_tokens=1500)

        return {
            "id": f"analysis-{_now().replace(':', '').replace('-', '')}",
            "timestamp": _now(),
            "fred_signals_count": len(fred_signals),
            "edgar_signals_count": len(edgar_signals),
            "analysis": analysis_text,
            "source": "claude",
        }

    # ── Logging ───────────────────────────────────────────────

    def _log(self, event: str, detail: str) -> None:
        self._scan_log.append({
            "timestamp": _now(),
            "event": event,
            "detail": detail,
        })
        # Keep last 100 entries
        if len(self._scan_log) > 100:
            self._scan_log = self._scan_log[-100:]

    # ── Public API ────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "last_scan": self._last_scan,
            "total_scans": sum(1 for l in self._scan_log if l["event"] == "SCAN COMPLETE"),
            "total_findings": len(self._findings),
            "interval_seconds": SCAN_INTERVAL,
            "sources": ["FRED", "SEC EDGAR"],
            "ai_engine": ANTHROPIC_MODEL,
        }

    def get_log(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._scan_log[-limit:]

    def get_findings(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._findings[-limit:]
