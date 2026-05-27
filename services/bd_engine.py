"""
Business Development Engine — EagleEye + Morgan + Aria working together.

This is the autonomous deal sourcing machine:
1. EagleEye scans for signals (EDGAR, permits, news, EMMA, web)
2. System matches signals to deal opportunities by sector/size/type
3. Morgan generates custom pitch materials for each target
4. Aria sequences outreach campaigns
5. Responses funnel into deal intake automatically

When a sub-industry silo is triggered (3+ deals in a sector),
the BD engine focuses its scanning on that sector.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

from agents._claude import complete


# ── Signal Sources ────────────────────────────────────────────

SIGNAL_SOURCES = {
    "edgar": {
        "description": "SEC filings — Form D (private placements), 8-K (material events), S-1 (IPOs)",
        "scan_interval_hours": 24,
    },
    "emma": {
        "description": "MSRB municipal bond filings — new issuances, continuing disclosures",
        "scan_interval_hours": 24,
    },
    "permits": {
        "description": "Construction permits, certificates of need, zoning applications",
        "scan_interval_hours": 168,  # weekly
    },
    "news": {
        "description": "Industry news — senior living, healthcare, real estate development",
        "scan_interval_hours": 12,
    },
    "linkedin": {
        "description": "Executive movements, company updates, fundraising signals",
        "scan_interval_hours": 48,
    },
    "conferences": {
        "description": "Industry conferences — LeadingAge, NIC, ASHA, NAHB",
        "scan_interval_hours": 720,  # monthly
    },
}

# ── Target Qualification Criteria ─────────────────────────────

QUALIFICATION_CRITERIA = {
    "senior_living": {
        "min_units": 50,
        "min_deal_size": 10_000_000,
        "signals": ["construction permit", "certificate of need", "bond filing", "acquisition", "expansion", "refinancing"],
        "disqualifiers": ["bankruptcy", "fraud", "SEC enforcement"],
    },
    "default": {
        "min_deal_size": 5_000_000,
        "signals": ["financing", "acquisition", "construction", "development", "expansion"],
        "disqualifiers": ["bankruptcy", "fraud", "SEC enforcement"],
    },
}


class BDEngine:
    """Autonomous business development — scan, qualify, pitch, outreach."""

    def scan_sector(self, sector: str, keywords: list[str] = None) -> list[dict]:
        """Scan all signal sources for a sector. Returns qualified targets."""
        if not keywords:
            criteria = QUALIFICATION_CRITERIA.get(sector, QUALIFICATION_CRITERIA["default"])
            keywords = criteria.get("signals", [])

        targets = []

        # EDGAR scan
        try:
            from services.data_connectors import EDGARPlugin
            edgar = EDGARPlugin()
            for kw in keywords[:3]:
                result = edgar.execute(prompt=f"{sector.replace('_', ' ')} {kw}", filing_type="D")
                for f in result.get("filings", []):
                    if f.get("name"):
                        targets.append({
                            "source": "edgar",
                            "name": f["name"],
                            "signal": kw,
                            "date": f.get("date", ""),
                            "url": f.get("url", ""),
                        })
        except Exception:
            pass

        return targets

    def generate_pitch(self, target: dict, sector: str = "senior_living") -> dict:
        """Generate a custom pitch for a target using Bernard + Morgan."""
        prompt = f"""Generate a concise pitch for NEST Advisors to approach this target:

Target: {target.get('name', 'Unknown')}
Location: {target.get('location', 'Unknown')}
Estimated Deal Size: ${target.get('size', 0):,.0f}
Status: {target.get('status', 'Unknown')}
Signal: {target.get('signal', 'Unknown')}
Sector: {sector}

NEST's credentials:
- Digital investment bank specializing in bond financing
- Currently financing $205M CCRC refinancing (Jacaranda Trace, Venice FL)
- $172.5M new construction CCRC (Convivial St. Petersburg)
- Sector-specific intelligence engine with real S&P/Moody's benchmarks
- Two principals, AI-powered platform, institutional-quality execution

Generate:
1. ONE-PARAGRAPH PITCH (what we offer this specific target)
2. RECOMMENDED STRUCTURE (what bond type/structure fits their situation)
3. ESTIMATED ECONOMICS (fee range, rate range, term)
4. NEXT STEP (specific action — call, email, conference meeting)
"""
        response = complete(
            "You are a senior investment banker at NEST Advisors. Direct, no hedging. Lead with the value proposition.",
            prompt,
            max_tokens=1024,
        )

        return {
            "target": target.get("name", ""),
            "pitch": response,
            "generated_at": datetime.utcnow().isoformat(),
            "sector": sector,
        }

    def generate_outreach_email(self, target: dict, pitch: dict) -> dict:
        """Generate an outreach email for Aria to send."""
        prompt = f"""Write a brief, professional outreach email from NEST Advisors to:

Target: {target.get('name', '')}
Contact: {target.get('contact_name', 'the CFO/CEO')}
Their situation: {target.get('status', '')}

Our pitch: {pitch.get('pitch', '')[:500]}

Email should be:
- 150 words max
- Professional but warm
- Specific to their situation
- Clear call to action (15-minute call)
- Signed by Sean Gilmore & Josh Edwards, Co-Founders

Do NOT be generic. Reference their specific project/situation."""

        email_body = complete(
            "You are writing outreach emails for NEST Advisors. Professional institutional tone.",
            prompt,
            max_tokens=512,
        )

        return {
            "to": target.get("contact_email", ""),
            "subject": f"NEST Advisors — Bond Financing for {target.get('name', 'Your Project')}",
            "body": email_body,
            "status": "draft",
            "target": target.get("name", ""),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def generate_campaign(self, targets: list[dict], sector: str = "senior_living") -> dict:
        """Generate a full outreach campaign for a list of targets.

        Each target gets: pitch, email draft, follow-up sequence, timeline.
        """
        campaign = {
            "sector": sector,
            "targets": len(targets),
            "created_at": datetime.utcnow().isoformat(),
            "pitches": [],
            "emails": [],
            "timeline": [
                {"day": 1, "action": "Send intro emails to all targets"},
                {"day": 4, "action": "LinkedIn connection requests with personalized notes"},
                {"day": 8, "action": "Follow-up email to non-responders"},
                {"day": 15, "action": "Phone call attempt to top 5 targets"},
                {"day": 22, "action": "Second follow-up with market update / comparable deal data"},
                {"day": 30, "action": "Final touch — conference invite or case study share"},
            ],
        }

        for target in targets[:5]:  # Limit to 5 to manage AI calls
            pitch = self.generate_pitch(target, sector)
            campaign["pitches"].append(pitch)

        return campaign

    def qualify_target(self, target: dict, sector: str = "senior_living") -> dict:
        """Score a target's deal potential."""
        criteria = QUALIFICATION_CRITERIA.get(sector, QUALIFICATION_CRITERIA["default"])
        score = 0
        flags = []

        size = target.get("size", 0)
        if size >= criteria.get("min_deal_size", 5_000_000):
            score += 30
            flags.append("Deal size meets minimum")
        else:
            flags.append("Deal size below minimum")

        if target.get("status") in ["construction", "expansion", "planning"]:
            score += 25
            flags.append("Active development signal")

        if target.get("signal") in criteria.get("signals", []):
            score += 20
            flags.append(f"Signal match: {target.get('signal')}")

        if target.get("location", "").endswith("FL"):
            score += 15
            flags.append("Florida market — NEST home territory")

        for disq in criteria.get("disqualifiers", []):
            if disq in str(target).lower():
                score = 0
                flags = ["DISQUALIFIED: " + disq]
                break

        return {
            "target": target.get("name", ""),
            "score": score,
            "max_score": 100,
            "qualified": score >= 40,
            "flags": flags,
        }

    def silo_check(self, deals: list[dict]) -> dict:
        """Check if any sector has hit the sub-industry silo threshold."""
        sector_counts = {}
        for deal in deals:
            sector = deal.get("sector", "unknown")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        silos_triggered = {}
        for sector, count in sector_counts.items():
            if count >= 3:
                silos_triggered[sector] = {
                    "count": count,
                    "status": "SILO_TRIGGERED",
                    "capabilities": [
                        f"{sector}-specific credit policy overlay",
                        f"{sector}-specific template library",
                        f"{sector}-specific rating calibration",
                        f"{sector}-specific buyer pool intelligence",
                        f"{sector}-specific BD outreach",
                    ],
                }
            elif count >= 2:
                silos_triggered[sector] = {
                    "count": count,
                    "status": "APPROACHING_THRESHOLD",
                    "needed": 3 - count,
                }

        return silos_triggered
