"""
NEST Advisors — Desk Registry
Maps the firm's organizational structure per the Operating Framework v1.
14 operational desks + Orca C-suite, each mirroring institutional counterparts.

Two principals (Sean Gilmore, Josh Edwards) + AI agent workforce.
Bond lending is the sole product. The platform is the moat.
"""

ORCA_CSUITE = {
    "ceo": {"name": "Bernard", "role": "CEO / Platform Orchestrator", "agent_file": "bernard.py"},
    "cfo": {"name": "CFO Agent", "role": "Revenue & Fee Tracking", "agent_file": None},
    "coo": {"name": "COO Agent", "role": "Workflow Orchestration", "agent_file": None},
    "cto": {"name": "CTO Agent", "role": "Platform Health & Monitoring", "agent_file": None},
    "head_bd": {"name": "Head of BD", "role": "EagleEye Coordination", "agent_file": None},
    "cco": {"name": "In-House Counsel / CCO", "role": "Compliance Gating", "agent_file": None},
}

DESKS = {
    "bond_desk": {
        "name": "Bond Desk",
        "description": "Deal origination, execution, and pipeline management",
        "agents": {
            "md": {"name": "MD Agent", "role": "Deal strategy, pricing decisions, exception authority", "agent_file": None},
            "vp": {"name": "VP Agent", "role": "Deal execution, working group coordination", "agent_file": "bond_optimizer.py", "existing_agent": "BondOptimizer"},
            "associate": {"name": "Associate Agent", "role": "Credit memo drafting, model building", "agent_file": None},
            "analyst": {"name": "Analyst Agent", "role": "Data gathering, comp analysis, market research", "agent_file": None},
            "market_signals": {"name": "Vector", "role": "Market signals monitoring (14 signals, 15-min)", "agent_file": "vector_agent.py", "existing_agent": "Vector"},
            "rate_management": {"name": "Apex", "role": "Rate hedging, short position management", "agent_file": "apex_agent.py", "existing_agent": "Apex"},
        },
        "platform_components": ["bond_structuring", "bond_tools", "bond_workflow", "market"],
    },
    "credit_underwriting": {
        "name": "Credit Underwriting Desk",
        "description": "Credit analysis, memo production, credit policy enforcement",
        "agents": {
            "senior_underwriter": {"name": "Maxwell", "role": "Senior Credit Underwriter — DSCR, LTV, LGD, obligor grading", "agent_file": "maxwell.py", "existing_agent": "Maxwell"},
            "credit_analyst": {"name": "Credit Analyst", "role": "Supporting credit analysis", "agent_file": None},
            "credit_committee": {"name": "Credit Committee", "role": "Committee package production", "agent_file": None},
        },
        "platform_components": ["bond_tools", "risk", "engines_api"],
    },
    "structuring": {
        "name": "Structuring Desk",
        "description": "Bond structure design, modeling, amortization, optionality",
        "agents": {
            "structuring_lead": {"name": "Prometheus", "role": "Financial modeling engine — proforma, stress, feasibility", "agent_file": "prometheus.py", "existing_agent": "Prometheus"},
            "structuring_analyst": {"name": "Structuring Analyst", "role": "Structure analysis support", "agent_file": None},
        },
        "platform_components": ["bond_structuring", "engines_api"],
    },
    "rating": {
        "name": "Rating Desk",
        "description": "Rating prediction, agency methodology mirroring, rating advisory",
        "agents": {
            "moodys_mirror": {"name": "Moody's Mirror Agent", "role": "Apply Moody's published methodology to predict ratings", "agent_file": "moodys_mirror.py", "new": True},
            "sp_mirror": {"name": "S&P Mirror Agent", "role": "Apply S&P published methodology to predict ratings", "agent_file": "sp_mirror.py", "new": True},
            "rating_coordinator": {"name": "Rating Coordinator", "role": "Agency selection, presentation strategy", "agent_file": None},
        },
        "platform_components": ["rating_esg", "intelligence"],
    },
    "documents": {
        "name": "Documents Desk",
        "description": "Document production, template management, version control",
        "agents": {
            "documents_lead": {"name": "Documents Lead", "role": "Document package coordination", "agent_file": None},
            "drafting": {"name": "Morgan", "role": "Document drafting, content generation (Jimmy Lee tone)", "agent_file": "morgan.py", "existing_agent": "Morgan"},
            "version_control": {"name": "Version Control Agent", "role": "Redline tracking, version management", "agent_file": None},
        },
        "platform_components": ["documents"],
    },
    "legal_compliance": {
        "name": "Legal & Compliance Desk",
        "description": "Regulatory compliance, securities law, tax compliance, KYC/AML",
        "agents": {
            "transaction_counsel": {"name": "Transaction Counsel", "role": "Deal-level legal coordination", "agent_file": None},
            "regulatory": {"name": "Regulatory Compliance", "role": "MSRB, SEC, state regulatory", "agent_file": None},
            "securities_law": {"name": "Securities Law", "role": "Rule 144A, Reg D, Reg S compliance", "agent_file": None},
            "tax": {"name": "Tax Compliance", "role": "IRC 103-150 compliance", "agent_file": None},
            "continuing_disclosure": {"name": "Continuing Disclosure", "role": "Rule 15c2-12, EMMA filings", "agent_file": None},
            "kyc_aml": {"name": "KYC/AML Agent", "role": "OFAC, PEP, sanctions screening", "agent_file": None},
            "conflicts_ethics": {"name": "Conflicts & Ethics", "role": "Conflict checking, ethics compliance", "agent_file": None},
            "litigation": {"name": "Litigation & Dispute", "role": "Litigation monitoring, dispute resolution", "agent_file": None},
            "document_retention": {"name": "Document Retention", "role": "Records management, retention policy", "agent_file": None},
            "msrb_rules": {"name": "MSRB Rules", "role": "G-37 Pay-to-Play, G-42 Fiduciary, G-17, G-44", "agent_file": None},
        },
        "platform_components": ["nightvision", "due_diligence"],
    },
    "trustee_liaison": {
        "name": "Trustee Liaison Desk",
        "description": "Trustee relationship management, fee benchmarking, performance tracking",
        "agents": {
            "relationship_mgr": {"name": "Trustee Relationship Manager", "role": "Trustee selection, relationship cultivation", "agent_file": None},
            "fee_benchmarking": {"name": "Fee Benchmarking Agent", "role": "Trustee fee comparison and negotiation", "agent_file": None},
            "performance": {"name": "Performance Tracking", "role": "Trustee service quality monitoring", "agent_file": None},
            "doc_coordination": {"name": "Document Coordination", "role": "Trustee document management", "agent_file": None},
            "reporting": {"name": "Reporting Agent", "role": "Trustee reporting requirements", "agent_file": None},
        },
        "counterparties": [
            "U.S. Bank", "BNY Mellon", "Wilmington Trust", "UMB Bank",
            "Zions Bank", "Computershare Trust Company", "Regions Trust", "Truist",
        ],
        "platform_components": ["rating_esg"],
    },
    "construction_risk": {
        "name": "Construction Risk Management Desk",
        "description": "Construction draw processing, budget tracking, schedule monitoring",
        "agents": {
            "draw_processing": {"name": "Draw Processing Agent", "role": "Construction draw verification and processing", "agent_file": None},
            "budget_tracking": {"name": "Budget vs Actual", "role": "Budget tracking, variance analysis", "agent_file": None},
            "schedule": {"name": "Schedule Monitor", "role": "Construction schedule tracking", "agent_file": None},
            "change_orders": {"name": "Change Order Agent", "role": "Change order management and approval", "agent_file": None},
            "lien_monitor": {"name": "Lien Monitor", "role": "Lien waiver tracking, mechanic's lien protection", "agent_file": None},
            "insurance_verify": {"name": "Insurance Verification", "role": "Builder's risk, coverage verification", "agent_file": None},
            "equity_tracking": {"name": "Sponsor Equity Tracking", "role": "Equity contribution draw schedule", "agent_file": None},
            "construction_monitor": {"name": "Construction Monitor Liaison", "role": "Third-party monitor coordination", "agent_file": None},
            "completion": {"name": "Completion Tracking", "role": "Substantial completion milestone tracking", "agent_file": None},
            "cap_i": {"name": "Cap-I Reserve Agent", "role": "Capitalized interest reserve management", "agent_file": None},
            "builders_risk": {"name": "Builder's Risk Agent", "role": "Builder's risk insurance management", "agent_file": None},
            "compliance_monitor": {"name": "Auditor", "role": "Construction compliance monitoring", "agent_file": "auditor.py", "existing_agent": "Auditor"},
        },
        "platform_components": ["treasury", "phoenix"],
    },
    "enhancement": {
        "name": "Insurance, Surety & Credit Enhancement Desk",
        "description": "Credit enhancement strategy, LOC, bond insurance, surety, federal guarantees",
        "agents": {
            "strategy": {"name": "Enhancement Strategy Agent", "role": "Enhancement selection and optimization", "agent_file": None},
            "loc_bank": {"name": "LOC Bank Liaison", "role": "Letter of credit bank coordination", "agent_file": None},
            "bond_insurer": {"name": "Bond Insurer Liaison", "role": "BAM, Assured Guaranty coordination", "agent_file": None},
            "surety": {"name": "SuretyScout", "role": "Surety bond sourcing and matching", "agent_file": "surety_scout.py", "existing_agent": "SuretyScout"},
            "federal_programs": {"name": "Federal Guarantee Programs", "role": "FHA 221(d)(4), 223(f), 232, 242; USDA B&I; GNMA wrap", "agent_file": None},
        },
        "counterparties": {
            "bond_insurers": ["Assured Guaranty (AGM, AGC)", "Build America Mutual (BAM)", "Berkshire Hathaway Assurance"],
            "loc_banks": ["JPMorgan Chase", "Bank of America", "Wells Fargo", "Citi", "PNC Bank", "TD Bank", "RBC", "Mizuho", "MUFG"],
        },
        "platform_components": ["surety"],
    },
    "placement": {
        "name": "Placement Desk",
        "description": "Bond placement, investor matching, order book, pricing analysis",
        "agents": {
            "book_building": {"name": "Sterling", "role": "Investor placement, CRM, book building", "agent_file": "sterling.py", "existing_agent": "Sterling"},
            "pricing_analyst": {"name": "Pricing Analyst", "role": "Comparable transaction pricing, spread analysis", "agent_file": None},
            "bd_partner": {"name": "BD Partner Interface", "role": "Broker-dealer coordination", "agent_file": None},
            "lender_sourcing": {"name": "LenderScout", "role": "Direct lender sourcing, 800+ database", "agent_file": "lender_scout.py", "existing_agent": "LenderScout"},
        },
        "counterparties": [
            "Piper Sandler", "Stifel Financial", "Hilltop Securities", "Raymond James",
            "BOK Financial Securities", "RBC Capital Markets", "Robert W. Baird",
            "Janney Montgomery Scott", "B.C. Ziegler", "HJ Sims",
        ],
        "platform_components": ["hawkeye", "investors", "lenders_api"],
    },
    "operations": {
        "name": "Operations Desk",
        "description": "Post-closing administration, debt service, covenant monitoring",
        "agents": {
            "debt_service": {"name": "Debt Service Admin", "role": "Debt service calculations per indenture", "agent_file": None},
            "compliance": {"name": "EMMA Compliance Agent", "role": "Continuing disclosure, EMMA filings", "agent_file": None},
            "covenant_monitor": {"name": "Covenant Monitor", "role": "Quarterly covenant testing workflow", "agent_file": None},
            "perm_debt": {"name": "Bridge", "role": "Perm debt monitoring, 18mo pre-stabilization", "agent_file": "bridge_agent.py", "existing_agent": "Bridge"},
            "blockchain": {"name": "Chain", "role": "On-chain deal recording", "agent_file": "chain_agent.py", "existing_agent": "Chain"},
        },
        "platform_components": ["perm", "blockchain", "rating_esg"],
    },
    "surveillance": {
        "name": "Surveillance Desk",
        "description": "Portfolio surveillance, refunding identification, restructuring, workouts",
        "agents": {
            "refunding": {"name": "Refunding ID Agent", "role": "NPV refunding calculation, rate savings identification", "agent_file": None},
            "restructuring": {"name": "Restructuring Agent", "role": "Restructuring opportunity identification", "agent_file": None},
            "risk_rerating": {"name": "Sentinel", "role": "Risk assessment, 7 dimensions, automated alerts", "agent_file": "sentinel.py", "existing_agent": "Sentinel"},
            "workout": {"name": "Workout Support", "role": "Distressed credit workout support", "agent_file": None},
        },
        "platform_components": ["risk", "convergence"],
    },
    "business_development": {
        "name": "Business Development Organization",
        "description": "Deal sourcing, outreach, pipeline management, conference presence",
        "agents": {
            "ma_intel": {"name": "Merlin", "role": "M&A intelligence, NAICS scan, target scoring", "agent_file": "merlin.py", "existing_agent": "Merlin"},
            "outreach": {"name": "Aria", "role": "Client outreach, cold/warm sequences", "agent_file": "aria.py", "existing_agent": "Aria"},
            "pipeline": {"name": "Pipeline Tracker", "role": "Deal pipeline analytics and tracking", "agent_file": None},
            "conference": {"name": "Conference & Brand", "role": "Conference strategy, brand presence", "agent_file": None},
        },
        "platform_components": ["eagleeye", "marketing", "scanner"],
    },
    "treasury": {
        "name": "Treasury Desk",
        "description": "Fund management, Ramp P-card program, construction draws, rebates",
        "agents": {
            "fund_optimizer": {"name": "Quantum", "role": "HFT fund optimizer, portfolio management", "agent_file": "quantum.py", "existing_agent": "Quantum"},
            "ramp_admin": {"name": "Ramp Admin Agent", "role": "Ramp API integration, card management", "agent_file": None},
            "draw_manager": {"name": "Draw Manager", "role": "Construction draw processing via Ramp", "agent_file": None},
        },
        "platform_components": ["treasury", "fund"],
    },
}


# ── Lookup helpers ────────────────────────────────────────────

def get_desk_for_agent(agent_name: str) -> dict | None:
    """Find which desk an agent belongs to."""
    for desk_id, desk in DESKS.items():
        for role_id, agent in desk["agents"].items():
            if agent.get("existing_agent") == agent_name or agent["name"] == agent_name:
                return {"desk_id": desk_id, "desk_name": desk["name"], "role_id": role_id, **agent}
    for role_id, agent in ORCA_CSUITE.items():
        if agent["name"] == agent_name:
            return {"desk_id": "orca", "desk_name": "Orca C-Suite", "role_id": role_id, **agent}
    return None


def get_all_agents() -> list[dict]:
    """Return flat list of all agents across all desks."""
    agents = []
    for role_id, agent in ORCA_CSUITE.items():
        agents.append({"desk": "orca", "desk_name": "Orca C-Suite", "role_id": role_id, **agent})
    for desk_id, desk in DESKS.items():
        for role_id, agent in desk["agents"].items():
            agents.append({"desk": desk_id, "desk_name": desk["name"], "role_id": role_id, **agent})
    return agents


def get_desk_agents(desk_id: str) -> list[dict]:
    """Return agents for a specific desk."""
    desk = DESKS.get(desk_id)
    if not desk:
        return []
    return [{"role_id": k, **v} for k, v in desk["agents"].items()]


def get_desk_summary() -> dict:
    """Return summary stats for all desks."""
    summary = {"orca": {"name": "Orca C-Suite", "agent_count": len(ORCA_CSUITE)}}
    for desk_id, desk in DESKS.items():
        wired = sum(1 for a in desk["agents"].values() if a.get("agent_file"))
        summary[desk_id] = {
            "name": desk["name"],
            "description": desk["description"],
            "agent_count": len(desk["agents"]),
            "wired_count": wired,
            "coverage_pct": round(wired / len(desk["agents"]) * 100) if desk["agents"] else 0,
        }
    return summary
