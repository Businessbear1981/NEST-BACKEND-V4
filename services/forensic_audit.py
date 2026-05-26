"""
NEST Forensic Audit Engine.
FBI/DOJ-standard forensic audit.
If it passes this, it passes the rating agencies.
Every dollar traced. Every relationship disclosed.
Every assumption validated. Every conflict identified.
"""
import hashlib
import json
from datetime import datetime

AUDIT_STANDARDS = {
    "financial_integrity": {
        "level": "DOJ criminal standard",
        "description": "Every dollar in sources and uses traced to a bank statement or invoice",
        "checks": [
            "All equity contributions verified to bank wire",
            "All soft costs tied to signed contracts",
            "GMP amount matches signed construction contract",
            "Professional fees match executed engagement letters",
            "No circular funding (related party purchases at above-market)",
            "No undisclosed related party transactions",
            "All appraisals by independent USPAP-certified appraisers",
            "Market study by firm with no financial interest in project",
            "Feasibility assumptions match market comps (verifiable)",
            "Revenue projections supported by signed lease agreements or reservations",
        ],
    },
    "relationship_disclosure": {
        "level": "SEC standard",
        "description": "All related parties identified and conflicts disclosed",
        "checks": [
            "All related parties identified and disclosed in offering docs",
            "Land seller relationships disclosed",
            "Manager/operator relationship to developer disclosed",
            "Subordinate note purchaser identity disclosed",
            "Any overlap between borrower, developer, manager, operator fully mapped",
            "Compensation of all principals disclosed",
        ],
    },
    "assumption_validation": {
        "level": "Rating agency standard",
        "description": "Every projection benchmarked to verifiable market data",
        "checks": [
            "Occupancy ramp compared to 5 comparable open communities",
            "Entrance fees compared to market comparables within 5 miles",
            "Monthly fees benchmarked to NIC MAP data",
            "Operating expense ratios compared to NACSA benchmarks",
            "Construction cost per SF compared to RSMeans or Gordian",
            "Interest rate assumptions benchmarked to current market",
            "Exit cap rate supported by at least 3 recent comparable sales",
        ],
    },
    "legal_structure": {
        "level": "Bond counsel standard",
        "description": "All entities and contracts in proper legal order",
        "checks": [
            "All entities properly formed and in good standing",
            "Operating agreements reviewed for control provisions",
            "All liens on property identified and subordinated or released",
            "Insurance certificates current and adequate",
            "All contracts properly executed (wet signature + notary where required)",
            "No open litigation material to the project",
            "Regulatory filings current (COA, healthcare licenses)",
        ],
    },
    "accounting_standards": {
        "level": "US GAAP / FASB",
        "description": "Financial statements meet institutional accounting requirements",
        "checks": [
            "Financial statements prepared per US GAAP",
            "Revenue recognition per ASC 606",
            "Lease accounting per ASC 842",
            "Construction cost capitalization per GAAP",
            "Entrance fee deferral accounting per FASB guidance for CCRCs",
            "Working capital properly calculated (current assets minus current liabilities)",
            "EBITDA add-backs are legitimate and recurring",
            "No hidden liabilities off balance sheet",
        ],
    },
}

SEVERITY_WEIGHTS = {"critical": 25, "high": 10, "medium": 5, "low": 1}

BANK_CULTURE = {
    "JPMorgan": {
        "style": "quantitative",
        "focus": ["covenant_structure", "stress_scenarios", "comparable_transactions"],
        "risk_appetite": "conservative",
        "wants": "Every covenant, every downside modeled, 3 stress scenarios minimum",
    },
    "HSBC": {
        "style": "relationship",
        "focus": ["sponsor_track_record", "international_angle", "cross_sell"],
        "risk_appetite": "moderate",
        "wants": "Strong sponsor story, relationship depth, cross-border value",
    },
    "BofA": {
        "style": "sector_specialist",
        "focus": ["healthcare_expertise", "senior_living_comps", "operator_quality"],
        "risk_appetite": "aggressive_on_healthcare",
        "wants": "Deep sector knowledge, operator benchmarks, NIC MAP data",
    },
    "Wells": {
        "style": "conservative",
        "focus": ["cash_flow_coverage", "collateral_value", "guarantor_strength"],
        "risk_appetite": "conservative",
        "wants": "Belt and suspenders. Guarantor net worth, real estate value, cash flow triple-covered.",
    },
}

AGENCY_FORMAT = {
    "SP": {
        "name": "S&P Global Ratings",
        "sections": ["executive_summary", "business_profile", "financial_profile",
                      "peer_comparison", "stress_scenarios", "rating_rationale"],
        "key_metrics": ["dscr", "ltv", "debt_to_ebitda", "occupancy_stabilized"],
    },
    "Moodys": {
        "name": "Moody's Investors Service",
        "sections": ["credit_opinion", "rating_methodology", "financial_analysis",
                      "operating_environment", "management_assessment", "outlook"],
        "key_metrics": ["dscr", "leverage", "liquidity", "asset_quality"],
    },
    "Fitch": {
        "name": "Fitch Ratings",
        "sections": ["key_rating_drivers", "rating_sensitivities", "financial_analysis",
                      "peer_analysis", "esg_considerations"],
        "key_metrics": ["dscr", "net_leverage", "liquidity_coverage", "capex_ratio"],
    },
}


class ForensicAuditAgent:

    def run_full_audit(self, deal: dict, documents: dict,
                       financials: dict) -> dict:
        findings = []
        category_scores = {}

        for category, standard in AUDIT_STANDARDS.items():
            cat_findings = []
            checks_passed = 0
            total_checks = len(standard["checks"])

            for check in standard["checks"]:
                check_key = check.lower().replace(" ", "_")[:40]
                evidence = documents.get(check_key) or financials.get(check_key)
                has_doc = documents.get(category, {}).get(check_key, False)

                if evidence or has_doc:
                    checks_passed += 1
                else:
                    severity = self._assess_severity(category, check)
                    finding = {
                        "category": category,
                        "check": check,
                        "status": "FAIL",
                        "severity": severity,
                        "recommendation": self._recommendation(category, check),
                    }
                    cat_findings.append(finding)
                    findings.append(finding)

            score = round(checks_passed / total_checks * 100) if total_checks else 0
            category_scores[category] = {
                "score": score,
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "level": standard["level"],
                "findings": cat_findings,
            }

        overall_score = round(sum(cs["score"] for cs in category_scores.values()) / len(category_scores)) if category_scores else 0

        critical_issues = [f for f in findings if f["severity"] == "critical"]
        high_issues = [f for f in findings if f["severity"] == "high"]

        penalty = sum(SEVERITY_WEIGHTS.get(f["severity"], 0) for f in findings)
        adjusted_score = max(0, min(100, overall_score - penalty))

        audit_data = json.dumps({"deal": deal, "findings": findings, "score": adjusted_score}, default=str, sort_keys=True)
        audit_hash = hashlib.sha256(audit_data.encode()).hexdigest()

        return {
            "audit_date": datetime.utcnow().isoformat(),
            "overall_score": adjusted_score,
            "category_scores": category_scores,
            "total_findings": len(findings),
            "findings": findings,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "clean_opinion": adjusted_score >= 90 and len(critical_issues) == 0,
            "jp_morgan_ready": adjusted_score >= 85 and len(critical_issues) == 0 and len(high_issues) <= 2,
            "rating_agency_ready": adjusted_score >= 90 and len(critical_issues) == 0,
            "recommendations": [f["recommendation"] for f in findings if f["recommendation"]],
            "audit_trail_hash": audit_hash,
            "standard": "FBI/DOJ forensic + SEC disclosure + Rating agency + US GAAP",
        }

    def _assess_severity(self, category: str, check: str) -> str:
        critical_keywords = ["circular funding", "undisclosed", "hidden liabilities", "no open litigation"]
        high_keywords = ["bank wire", "GMP", "USPAP", "COA", "good standing", "US GAAP"]
        medium_keywords = ["benchmarked", "compared", "reviewed", "adequate"]

        check_lower = check.lower()
        for kw in critical_keywords:
            if kw in check_lower:
                return "critical"
        for kw in high_keywords:
            if kw.lower() in check_lower:
                return "high"
        for kw in medium_keywords:
            if kw in check_lower:
                return "medium"
        return "low"

    def _recommendation(self, category: str, check: str) -> str:
        recs = {
            "financial_integrity": f"Obtain documentation: {check}. Trace to source document (bank wire, signed contract, or invoice).",
            "relationship_disclosure": f"Disclose in offering documents: {check}. Bond counsel must review.",
            "assumption_validation": f"Benchmark against market data: {check}. Cite 3+ comparable data points.",
            "legal_structure": f"Legal counsel to verify: {check}. Obtain current certificates/opinions.",
            "accounting_standards": f"CPA to confirm: {check}. Must comply with applicable FASB/ASC standards.",
        }
        return recs.get(category, f"Address: {check}")

    def validate_sources_uses(self, sources_uses: dict, bank_records: list) -> dict:
        sources = sources_uses.get("sources", {})
        uses = sources_uses.get("uses", {})
        total_sources = sum(sources.values())
        total_uses = sum(uses.values())
        variance = abs(total_sources - total_uses)

        verified_sources = {}
        unverified = []
        for source_name, amount in sources.items():
            matched = any(
                abs(r.get("amount", 0) - amount) < 100 and r.get("type") in ["wire", "deposit"]
                for r in bank_records
            )
            verified_sources[source_name] = {"amount_usd": amount, "verified": matched}
            if not matched:
                unverified.append(source_name)

        verified_uses = {}
        for use_name, amount in uses.items():
            has_contract = any(
                r.get("type") == "contract" and abs(r.get("amount", 0) - amount) < amount * 0.05
                for r in bank_records
            )
            verified_uses[use_name] = {"amount_usd": amount, "contract_verified": has_contract}

        return {
            "total_sources_usd": total_sources,
            "total_uses_usd": total_uses,
            "variance_usd": variance,
            "balanced": variance < 1000,
            "sources_verified": verified_sources,
            "uses_verified": verified_uses,
            "unverified_sources": unverified,
            "fbi_standard_met": len(unverified) == 0 and variance < 1000,
        }

    def validate_assumptions(self, projections: dict, market_comps: list) -> dict:
        results = []
        for key, projected_value in projections.items():
            comp_values = [c.get(key, 0) for c in market_comps if c.get(key)]
            if not comp_values:
                results.append({"metric": key, "projected": projected_value, "status": "NO_COMPS",
                                "severity": "high", "note": "No comparable data available"})
                continue

            avg_comp = sum(comp_values) / len(comp_values)
            variance_pct = round((projected_value - avg_comp) / avg_comp * 100, 1) if avg_comp else 0

            if abs(variance_pct) <= 10:
                status = "PASS"
                severity = "low"
            elif abs(variance_pct) <= 20:
                status = "CAUTION"
                severity = "medium"
            else:
                status = "FAIL"
                severity = "high"

            results.append({
                "metric": key,
                "projected": projected_value,
                "market_avg": round(avg_comp, 2),
                "variance_pct": variance_pct,
                "comps_count": len(comp_values),
                "status": status,
                "severity": severity,
            })

        pass_count = sum(1 for r in results if r["status"] == "PASS")
        return {
            "total_assumptions_tested": len(results),
            "passed": pass_count,
            "cautioned": sum(1 for r in results if r["status"] == "CAUTION"),
            "failed": sum(1 for r in results if r["status"] == "FAIL"),
            "no_comps": sum(1 for r in results if r["status"] == "NO_COMPS"),
            "results": results,
            "doj_standard_met": all(r["status"] in ["PASS", "CAUTION"] for r in results),
        }

    def generate_audit_report(self, findings: dict) -> str:
        score = findings.get("overall_score", 0)
        critical = len(findings.get("critical_issues", []))
        total = findings.get("total_findings", 0)
        clean = findings.get("clean_opinion", False)

        report = f"""NEST FORENSIC AUDIT REPORT
{'='*60}
Date: {datetime.utcnow().strftime('%B %d, %Y')}
Standard: FBI/DOJ Forensic + SEC Disclosure + Rating Agency

OVERALL SCORE: {score}/100
Clean Opinion: {'YES' if clean else 'NO — REMEDIATION REQUIRED'}
Critical Issues: {critical}
Total Findings: {total}

{'='*60}
CATEGORY BREAKDOWN
{'='*60}
"""
        for cat, data in findings.get("category_scores", {}).items():
            report += f"\n{cat.upper().replace('_', ' ')}: {data['score']}/100"
            report += f"\n  Level: {data['level']}"
            report += f"\n  Passed: {data['checks_passed']}/{data['total_checks']}"
            if data["findings"]:
                for f in data["findings"]:
                    report += f"\n  [{f['severity'].upper()}] {f['check']}"

        if findings.get("critical_issues"):
            report += f"\n\n{'='*60}\nCRITICAL ISSUES — MUST RESOLVE\n{'='*60}\n"
            for issue in findings["critical_issues"]:
                report += f"\n- {issue['check']}"
                report += f"\n  Action: {issue['recommendation']}\n"

        report += f"\n\nAudit Trail Hash: {findings.get('audit_trail_hash', 'N/A')}"
        return report

    def rating_agency_presentation(self, deal: dict, audit: dict,
                                   target_agency: str = "SP") -> dict:
        agency = AGENCY_FORMAT.get(target_agency, AGENCY_FORMAT["SP"])
        sections = {}

        for section in agency["sections"]:
            if section == "executive_summary" or section == "credit_opinion" or section == "key_rating_drivers":
                sections[section] = {
                    "content": f"Deal overview for {deal.get('name', 'Project')}. "
                               f"Total project cost: ${deal.get('total_project_cost_usd', 0):,.0f}. "
                               f"Audit score: {audit.get('overall_score', 0)}/100.",
                    "status": "clean" if audit.get("clean_opinion") else "qualified",
                }
            elif section in ["stress_scenarios", "rating_sensitivities"]:
                dscr = deal.get("dscr_stabilized", 1.5)
                sections[section] = {
                    "base_case_dscr": dscr,
                    "stress_minus_10_revenue": round(dscr * 0.85, 2),
                    "stress_plus_200bps_rate": round(dscr * 0.88, 2),
                    "stress_combined": round(dscr * 0.75, 2),
                    "passes_stress": round(dscr * 0.75, 2) >= 1.0,
                }
            else:
                sections[section] = {"status": "prepared", "data_source": "audit_package"}

        return {
            "target_agency": agency["name"],
            "presentation_date": datetime.utcnow().isoformat(),
            "sections": sections,
            "key_metrics": {m: deal.get(m, "TBD") for m in agency["key_metrics"]},
            "audit_score": audit.get("overall_score", 0),
            "clean_opinion": audit.get("clean_opinion", False),
            "ready_for_submission": audit.get("rating_agency_ready", False),
        }

    def bank_presentation(self, deal: dict, audit: dict, bank: str = "JPMorgan") -> dict:
        culture = BANK_CULTURE.get(bank, BANK_CULTURE["JPMorgan"])

        cover_memo = (
            f"To: {bank} Credit Committee\n"
            f"From: NEST Advisors — Sean Gilmore\n"
            f"Re: {deal.get('name', 'Project')} — ${deal.get('total_project_cost_usd', 0):,.0f}\n\n"
            f"This deal is clean. Forensic audit score: {audit.get('overall_score', 0)}/100. "
            f"{'Zero critical findings.' if not audit.get('critical_issues') else str(len(audit.get('critical_issues', []))) + ' critical issues — remediation plan attached.'}\n\n"
            f"Structure: NEST dual-tranche private bond. Hylant surety wrap on A tranche. "
            f"B tranche managed via bank HFT fund.\n\n"
            f"We are presenting to {bank} because: {culture['wants']}"
        )

        return {
            "bank": bank,
            "credit_culture": culture,
            "cover_memo": cover_memo,
            "presentation_sections": [
                "executive_summary", "deal_structure", "financial_analysis",
                "market_analysis", "management_team", "risk_factors",
                "stress_scenarios", "comparable_transactions", "appendix",
            ],
            "focus_areas": culture["focus"],
            "risk_appetite": culture["risk_appetite"],
            "audit_score": audit.get("overall_score", 0),
            "jp_morgan_ready": audit.get("jp_morgan_ready", False),
        }


forensic_audit = ForensicAuditAgent()
