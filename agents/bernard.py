"""
Bernard — CEO Agent / Platform Orchestrator
Answers any question across all desks. Action engine, not chatbot.
Professional institutional tone. Routes to specialized agents when needed.

Per Operating Framework v1: Bernard is the firm's CEO agent. All sessions live.
Doc upload auto-triggers parse->spread->ratios->memo chain.
Three modes: narrator, advisor, executor.
"""
from agents._claude import complete
from agents.desk_registry import DESKS, ORCA_CSUITE, get_all_agents

BERNARD_SYSTEM_PROMPT = """You are Bernard, the CEO and platform orchestrator for NEST Advisors — a digital commercial investment bank co-founded by Sean Gilmore and Josh Edwards.

Your role:
- Answer any question about the firm, its operations, its deals, its organizational structure
- Route operational tasks to the appropriate desk and agent
- Produce the weekly firm review, monthly financial report, quarterly strategic review
- Enforce the Operating Framework's architectural principles
- Provide tutorial explanations at decision points (tutorial/gate/wrap-up architecture)

Your tone: Professional institutional. Direct, decisive, no hedging. You speak like a senior banker — conclusions first, supporting data second. Never use: may, might, could, potentially, approximately, it seems.

The firm's organizational structure:
{desk_summary}

The firm's identity: Two principals plus the AI agent workforce. Bond lending is the sole product. The platform is the moat. Hiring is the failure mode. When capacity is hit, raise minimums — do not hire.

The firm's lead product is bond lending — origination, structuring, placement, and 30-year administration of middle-market bonds across investment grade and select non-investment grade categories, in both tax-exempt and taxable formats.

Bond Use Cases:
- M&A Acquisition Bonds (Chapter 1 — fully specified)
- Construction and Development Bonds (Chapter 2)
- Working Capital Bonds (Chapter 3)
- Equipment Bonds (Chapter 4)
- Real Estate Acquisition and Stabilization Bonds (Chapter 5)

Tagline: "It's Time To Fly"
"""


def _desk_summary() -> str:
    lines = ["ORCA C-SUITE:"]
    for role_id, agent in ORCA_CSUITE.items():
        lines.append(f"  - {agent['name']}: {agent['role']}")
    lines.append("")
    for desk_id, desk in DESKS.items():
        lines.append(f"{desk['name'].upper()}:")
        for role_id, agent in desk["agents"].items():
            lines.append(f"  - {agent['name']}: {agent['role']}")
        lines.append("")
    return "\n".join(lines)


class BernardAgent:
    """CEO / Platform Orchestrator — answers any question across all desks."""

    def __init__(self):
        self.name = "Bernard"
        self.role = "CEO / Platform Orchestrator"
        self.desk = "orca"

    def ask(self, question: str, context: dict | None = None) -> dict:
        """Ask Bernard any question about the firm or its operations."""
        system = BERNARD_SYSTEM_PROMPT.format(desk_summary=_desk_summary())
        if context:
            system += f"\n\nCurrent context:\n{_format_context(context)}"

        response = complete(system, question, max_tokens=4096)
        return {
            "agent": self.name,
            "desk": "orca",
            "role": self.role,
            "response": response,
            "routed_to": self._identify_routing(question),
        }

    def route(self, task: str) -> dict:
        """Route an operational task to the appropriate desk and agent."""
        routing_prompt = f"""Given this task, identify which desk and agent should handle it.
Return ONLY a JSON object with: {{"desk_id": "...", "role_id": "...", "agent_name": "...", "reason": "..."}}

Available desks and their agents:
{_desk_summary()}

Task: {task}"""
        system = "You are a routing engine for NEST Advisors. Return only valid JSON. Pick the single best desk and agent for this task."
        response = complete(system, routing_prompt, max_tokens=512)
        return {"task": task, "routing": response}

    def firm_review(self, deals: list = None, metrics: dict = None) -> str:
        """Produce the weekly firm review per Operating Framework cadence."""
        prompt = """Produce the weekly firm review for NEST Advisors. Cover:
1. Deal pipeline status — active deals, stage progression, blockers
2. Revenue tracking — fees earned, fees pending, projected close dates
3. Agent workforce performance — desk utilization, bottlenecks
4. Market conditions — rate environment, spread dynamics, issuance volume
5. Action items for the principals"""
        if deals:
            prompt += f"\n\nActive deals: {deals}"
        if metrics:
            prompt += f"\n\nPlatform metrics: {metrics}"
        system = BERNARD_SYSTEM_PROMPT.format(desk_summary=_desk_summary())
        return complete(system, prompt, max_tokens=4096)

    def tutorial(self, decision_point: str, context: dict = None) -> dict:
        """Tutorial/Gate/Wrap-up at a decision point.

        Per Operating Framework Build Priority 15: every significant decision
        point produces a tutorial explanation, a gate preventing progress without
        acknowledgment, and a wrap-up documenting the decision.
        """
        prompt = f"""At this decision point, provide three sections:

TUTORIAL: Explain what this decision means and why it matters. Write as if briefing a senior banker who understands finance but needs the specific context of this deal. 2-3 paragraphs.

GATE: State what the principal must acknowledge before proceeding. Be specific about the risk or commitment being accepted.

OPTIONS: List the available choices with trade-offs for each. Recommend one and explain why.

Decision point: {decision_point}
Context: {context or 'None provided'}"""
        system = BERNARD_SYSTEM_PROMPT.format(desk_summary=_desk_summary())
        response = complete(system, prompt, max_tokens=4096)
        return {
            "decision_point": decision_point,
            "tutorial": response,
            "requires_acknowledgment": True,
        }

    def narrate(self, event: str, deal_context: dict = None) -> str:
        """Narrator mode — explain what just happened in the deal workflow."""
        prompt = f"Narrate this event for the principals: {event}"
        if deal_context:
            prompt += f"\nDeal context: {deal_context}"
        system = BERNARD_SYSTEM_PROMPT.format(desk_summary=_desk_summary())
        return complete(system, prompt, max_tokens=2048)

    def _identify_routing(self, question: str) -> str | None:
        """Quick heuristic routing — which desk does this question relate to?"""
        q = question.lower()
        routing_map = {
            "bond_desk": ["bond", "deal", "pipeline", "issuance", "new issue"],
            "credit_underwriting": ["credit", "dscr", "ltv", "underwriting", "grade", "memo", "leverage"],
            "structuring": ["structure", "amortization", "model", "proforma", "tranche", "sizing"],
            "rating": ["rating", "moody", "s&p", "mirror", "methodology", "notch"],
            "documents": ["document", "template", "draft", "indenture", "official statement"],
            "legal_compliance": ["compliance", "regulatory", "kyc", "aml", "msrb", "sec", "tefra"],
            "trustee_liaison": ["trustee", "us bank", "bny mellon", "wilmington"],
            "construction_risk": ["construction", "draw", "change order", "lien", "builder", "gmp"],
            "enhancement": ["surety", "insurance", "loc", "letter of credit", "bam", "assured", "fha", "usda"],
            "placement": ["placement", "investor", "order book", "syndicate", "buyer", "allocation"],
            "operations": ["administration", "post-closing", "covenant monitor", "debt service", "continuing disclosure"],
            "surveillance": ["surveillance", "refunding", "restructuring", "workout", "distressed", "npv savings"],
            "business_development": ["sourcing", "outreach", "eagleeye", "conference", "sponsor", "inbound"],
            "treasury": ["treasury", "ramp", "card", "rebate", "fund", "hft", "soft cost", "t&e"],
        }
        for desk_id, keywords in routing_map.items():
            if any(kw in q for kw in keywords):
                return desk_id
        return None


def _format_context(context: dict) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in context.items())
