"""
Preflight Interview — Bernard-driven Q&A to complete the credit memo.

After docs are ingested, this interview fills the gaps that financials
can't answer. Bernard asks structured questions across 8 categories,
accepts answers, brainstorms when the user doesn't know, and builds
the deal narrative that feeds the credit memo.

Categories:
1. Transaction Overview — what are we doing and why
2. Sponsor / Management — who's behind this
3. Business Analysis — what does the company actually do
4. Industry Analysis — where does it sit in the market
5. Financial Analysis — what the docs showed + what's missing
6. Sources & Uses — how is this funded
7. Structural Preferences — rating target, enhancement, covenants
8. Risk Factors — what could go wrong

Each question has:
- The question itself
- Why it matters for the credit memo
- A brainstorm prompt if the user doesn't know
- What it feeds (credit memo section, rating input, structuring input)
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

from agents._claude import complete


INTERVIEW_SECTIONS = [
    {
        "id": "transaction_overview",
        "title": "Transaction Overview",
        "credit_memo_section": "EXECUTIVE SUMMARY",
        "questions": [
            {
                "id": "deal_thesis",
                "question": "What is this deal? In one paragraph — what are we financing, why does the borrower need bond financing, and why is a bond better than bank debt or equity for this project?",
                "why": "Opens the credit memo. The committee needs to understand the deal in 30 seconds.",
                "feeds": ["credit_memo", "investor_teaser"],
                "brainstorm": "Let's think through this: what problem does the borrower have that bond financing solves? Is it the amount (too large for banks), the term (needs 30-year money), the structure (needs construction + perm in one), or the cost (tax-exempt saves 200bps)?",
            },
            {
                "id": "use_of_proceeds",
                "question": "Specifically, what are the bond proceeds being used for? Break it down: acquisition cost, construction/renovation, refinancing existing debt, reserves, issuance costs, working capital.",
                "why": "Drives the Sources & Uses schedule — the most reviewed page in the credit package.",
                "feeds": ["sources_and_uses", "credit_memo"],
                "brainstorm": "Typical uses: purchase price or construction cost (60-75% of proceeds), reserves — DSRF + operating + cap-I (10-15%), issuance costs — legal, rating, trustee, underwriter (3-5%), working capital (5-10%). What's the primary use here?",
            },
            {
                "id": "timeline",
                "question": "What's the deal timeline? When do you need commitment, when does the deal need to close, and are there external deadlines driving the schedule?",
                "why": "Drives execution urgency and counterparty coordination.",
                "feeds": ["workflow", "working_group"],
            },
        ],
    },
    {
        "id": "sponsor_management",
        "title": "Sponsor & Management",
        "credit_memo_section": "BORROWER PROFILE",
        "questions": [
            {
                "id": "sponsor_background",
                "question": "Tell me about the sponsor. How long have they been operating, what's their track record in this sector, how many similar projects have they completed, and have they ever had a default or workout?",
                "why": "Sponsor quality is 20-30% of the rating. Strong sponsor = tighter pricing.",
                "feeds": ["credit_memo", "rating_submission"],
                "brainstorm": "Key things that matter: years of experience (7+ for construction, 3+ for stabilized), number of comparable projects completed, any defaults or litigation in the last 5 years, total AUM or net worth, and references from prior counterparties.",
            },
            {
                "id": "management_team",
                "question": "Who are the key management personnel? Who runs the day-to-day operations, and what happens if a key person leaves?",
                "why": "Management quality is a Moody's scorecard factor. Key-person risk affects the rating.",
                "feeds": ["credit_memo", "rating_submission"],
            },
            {
                "id": "sponsor_financial_capacity",
                "question": "Does the sponsor have the financial capacity to support this deal beyond the initial equity? Can they fund cost overruns, cover operating shortfalls during ramp-up, or inject additional equity if needed?",
                "why": "Sponsor support is a structural credit positive. Rated agencies look for it.",
                "feeds": ["credit_memo", "rating_submission", "enhancement"],
            },
        ],
    },
    {
        "id": "business_analysis",
        "title": "Business Analysis",
        "credit_memo_section": "BUSINESS ANALYSIS",
        "questions": [
            {
                "id": "business_description",
                "question": "Describe the business or project in detail. What does it do, who are its customers, what's the revenue model, and what makes it defensible?",
                "why": "The credit committee needs to understand the business before they'll approve the credit.",
                "feeds": ["credit_memo", "investor_teaser"],
                "brainstorm": "Think about: what service or product does this provide, who pays for it (and how reliable are those payers), is there a contract or recurring revenue base, what's the competitive advantage (location, brand, cost structure, regulatory moat)?",
            },
            {
                "id": "revenue_model",
                "question": "How does revenue work? Is it recurring (monthly fees, leases, contracts) or transactional? What percentage is contractually committed vs at-risk? What's the customer concentration — does any single customer represent more than 10% of revenue?",
                "why": "Revenue quality drives the financial risk profile. Recurring > transactional. Diversified > concentrated.",
                "feeds": ["credit_memo", "rating_submission"],
            },
            {
                "id": "competitive_position",
                "question": "Where does this business sit competitively? Who are the main competitors, what market share does the borrower have, and what barriers to entry protect the business?",
                "why": "S&P Business Risk Profile factor. Competitive position is 30% of the business risk score.",
                "feeds": ["credit_memo", "rating_submission"],
                "brainstorm": "Consider: is this a fragmented market where the borrower has scale advantages? Is there a regulatory barrier (licensing, permits, certificates of need)? Geographic advantage (the only facility in a 20-mile radius)? Brand or reputation advantage?",
            },
        ],
    },
    {
        "id": "industry_analysis",
        "title": "Industry Analysis",
        "credit_memo_section": "INDUSTRY ANALYSIS",
        "questions": [
            {
                "id": "industry_overview",
                "question": "What industry is this and what are the key trends? Is the sector growing, stable, or declining? What's driving demand? Are there headwinds or tailwinds?",
                "why": "S&P Industry Risk is the first factor in the Business Risk Profile. Moody's Market Position is 45% of the healthcare scorecard.",
                "feeds": ["credit_memo", "rating_submission"],
                "brainstorm": "I can pull industry data from our intelligence layer. What NAICS code is this? I'll look up sector growth rates, market size, and recent transaction activity.",
            },
            {
                "id": "regulatory_environment",
                "question": "What regulatory framework governs this business? Are there licensing requirements, certificates of need, government approvals needed? Is the regulatory environment favorable or challenging?",
                "why": "Regulatory risk is a key factor in both Moody's and S&P assessments.",
                "feeds": ["credit_memo", "compliance"],
            },
            {
                "id": "market_study",
                "question": "Is there a market study or feasibility study? If yes, what does it show for demand, supply pipeline, and absorption? If no, do we need to commission one?",
                "why": "Market studies support the revenue assumptions in the proforma. Rating agencies want third-party validation.",
                "feeds": ["credit_memo", "rating_submission", "doc_checklist"],
            },
        ],
    },
    {
        "id": "financial_analysis",
        "title": "Financial Analysis",
        "credit_memo_section": "FINANCIAL ANALYSIS",
        "questions": [
            {
                "id": "financial_trends",
                "question": "Looking at the financials we've extracted, are there any trends I should understand? Revenue growth or decline, margin compression, one-time items, changes in the business model?",
                "why": "Trend analysis is critical — a 1.5x DSCR that's declining is very different from one that's improving.",
                "feeds": ["credit_memo"],
            },
            {
                "id": "proforma_assumptions",
                "question": "Walk me through the key assumptions in the proforma. What revenue growth rate are you assuming, what occupancy or utilization at stabilization, what expense growth, and when does the project stabilize?",
                "why": "The credit committee will stress-test every assumption. We need to defend each one.",
                "feeds": ["credit_memo", "modeling"],
                "brainstorm": "Typical assumptions to validate: revenue growth (2-3% for stabilized, higher for ramp-up), occupancy at stabilization (90-95% for most sectors), expense growth (3-4%), stabilization timeline (12-24 months for ramp, 24-36 for construction). What does the proforma assume?",
            },
            {
                "id": "capital_expenditure",
                "question": "What are the ongoing capital expenditure requirements? Is this a capital-intensive business? Are there deferred maintenance issues? What's the annual capex budget?",
                "why": "Capex affects free cash flow and the (EBITDA-Capex)/Interest coverage ratio that Moody's uses.",
                "feeds": ["credit_memo", "rating_submission"],
            },
        ],
    },
    {
        "id": "sources_and_uses",
        "title": "Sources & Uses",
        "credit_memo_section": "CAPITAL STRUCTURE",
        "questions": [
            {
                "id": "total_cost",
                "question": "What's the total project cost or acquisition price? And how is it being funded — what are all the sources?",
                "why": "The S&U schedule must balance. Every dollar of cost needs a source.",
                "feeds": ["sources_and_uses", "credit_memo"],
            },
            {
                "id": "equity_contribution",
                "question": "How much equity is the sponsor putting in? Is it cash at closing, or is some deferred? Is there rollover equity from existing owners?",
                "why": "Equity contribution drives LTV and is a key factor in the rating. More equity = better rating.",
                "feeds": ["credit_memo", "rating_submission", "structuring"],
            },
            {
                "id": "existing_debt",
                "question": "Is there existing debt being refinanced? If so, what are the terms, who holds it, and what's the outstanding balance?",
                "why": "Refunding economics — are we saving the borrower money by refinancing?",
                "feeds": ["sources_and_uses", "credit_memo"],
            },
        ],
    },
    {
        "id": "structural_preferences",
        "title": "Structural Preferences",
        "credit_memo_section": "STRUCTURAL ANALYSIS",
        "questions": [
            {
                "id": "target_rating",
                "question": "What rating are you targeting? Investment grade (BBB or better) or high yield (BB or below)? Do you have a preference for Moody's, S&P, or both?",
                "why": "The target rating drives every structural decision — covenants, reserves, enhancement, pricing.",
                "feeds": ["rating_submission", "structuring"],
                "brainstorm": "Investment grade (BBB/Baa) gets you the broadest investor base and tightest pricing but requires stronger metrics. High yield (BB/Ba) allows more leverage but limits investors to HY funds and is more expensive. Based on what I've seen in the docs, I'd suggest targeting...",
            },
            {
                "id": "enhancement_preference",
                "question": "Are you considering credit enhancement — bond insurance, letter of credit, surety, or federal guarantee (FHA/USDA)? Or standalone on the borrower's native credit?",
                "why": "Enhancement can lift the rating 3-5 notches and dramatically widen the buyer pool.",
                "feeds": ["enhancement", "structuring", "placement"],
            },
            {
                "id": "tax_status",
                "question": "Is this deal tax-exempt eligible? Is the borrower a 501(c)(3)? Does the project qualify under IRC §142 as a private activity bond? Or is this taxable?",
                "why": "Tax-exempt saves 150-250bps in coupon. If the deal qualifies, tax-exempt is almost always the right answer.",
                "feeds": ["structuring", "legal_compliance"],
            },
        ],
    },
    {
        "id": "risk_factors",
        "title": "Risk Factors",
        "credit_memo_section": "RISK FACTORS",
        "questions": [
            {
                "id": "top_risks",
                "question": "What are the top 3-5 risks you see in this deal? What could go wrong, and what mitigants exist?",
                "why": "Every credit memo needs a risk section. Better to identify them upfront than have the committee find them.",
                "feeds": ["credit_memo"],
                "brainstorm": "Common risk categories: construction risk (cost overruns, delays), market risk (demand falls short), management risk (key person leaves), regulatory risk (permits, licensing), interest rate risk (rates rise before closing), sponsor risk (financial distress). Which of these apply here?",
            },
            {
                "id": "worst_case",
                "question": "What's the downside scenario? If the proforma assumptions don't materialize, what's the floor — can the project still service debt at 75% of projected revenue?",
                "why": "Stress testing is required by both rating agencies. We need to show the deal works even under adverse conditions.",
                "feeds": ["credit_memo", "modeling"],
            },
        ],
    },
]


class PreflightInterview:
    """Bernard-driven Q&A to complete the credit memo."""

    def __init__(self):
        self.name = "Preflight Interview"

    def get_questions(self, deal: dict = None) -> list[dict]:
        """Return all interview sections with questions.

        If deal data provided, marks which questions are already answered
        from the document ingestion.
        """
        sections = []
        for section in INTERVIEW_SECTIONS:
            questions = []
            for q in section["questions"]:
                answered = False
                if deal:
                    # Check if this question's data exists from doc ingestion
                    if q["id"] == "deal_thesis" and deal.get("description"):
                        answered = True
                    elif q["id"] == "total_cost" and deal.get("total_project_cost"):
                        answered = True
                    elif q["id"] == "equity_contribution" and deal.get("equity_pct"):
                        answered = True
                    elif q["id"] == "existing_debt" and deal.get("existing_debt"):
                        answered = True

                questions.append({
                    **q,
                    "answered": answered,
                    "answer": deal.get(q["id"]) if deal else None,
                })

            answered_count = sum(1 for q in questions if q["answered"])
            sections.append({
                "id": section["id"],
                "title": section["title"],
                "credit_memo_section": section["credit_memo_section"],
                "questions": questions,
                "total": len(questions),
                "answered": answered_count,
                "complete": answered_count == len(questions),
            })
        return sections

    def get_next_question(self, deal: dict = None, answers: dict = None) -> dict | None:
        """Return the next unanswered question."""
        answers = answers or {}
        for section in INTERVIEW_SECTIONS:
            for q in section["questions"]:
                if q["id"] not in answers:
                    return {
                        "section": section["title"],
                        "credit_memo_section": section["credit_memo_section"],
                        **q,
                    }
        return None  # All answered

    def brainstorm(self, question_id: str, deal: dict = None) -> str:
        """When user doesn't know the answer, Bernard brainstorms."""
        # Find the question
        question = None
        for section in INTERVIEW_SECTIONS:
            for q in section["questions"]:
                if q["id"] == question_id:
                    question = q
                    break

        if not question:
            return "I don't have a brainstorm for that question."

        if question.get("brainstorm"):
            context = question["brainstorm"]
        else:
            context = f"The user needs help answering: {question['question']}"

        if deal:
            context += f"\n\nDeal context: sector={deal.get('sector')}, type={deal.get('deal_type')}, size=${deal.get('bond_amount',0):,.0f}"

        prompt = f"""You are Bernard, CEO of NEST Advisors. A deal team member needs help
answering a credit memo question. Help them think through it.

Question: {question['question']}
Why it matters: {question['why']}

Context: {context}

Be direct, suggest specific approaches, and if possible propose a draft answer
they can refine. Don't hedge."""

        return complete(
            "You are Bernard — NEST Advisors CEO. Professional institutional tone. Direct, no hedging.",
            prompt,
            max_tokens=2048,
        )

    def generate_deal_narrative(self, answers: dict, deal: dict = None) -> str:
        """Generate a complete deal narrative from interview answers.

        This becomes the foundation of the credit memo.
        """
        sections_text = []
        for section in INTERVIEW_SECTIONS:
            section_answers = []
            for q in section["questions"]:
                answer = answers.get(q["id"])
                if answer:
                    section_answers.append(f"Q: {q['question']}\nA: {answer}")

            if section_answers:
                sections_text.append(f"\n{section['title'].upper()}:\n" + "\n\n".join(section_answers))

        all_qa = "\n".join(sections_text)

        prompt = f"""Based on these interview responses, generate a complete deal narrative
suitable for the executive summary section of an institutional credit memo.

The narrative should:
1. Open with what the deal is and why it makes sense
2. Describe the borrower/sponsor and their qualifications
3. Summarize the business and competitive position
4. Highlight the key financial metrics
5. Note the proposed structure
6. Acknowledge top risks with mitigants
7. Conclude with the credit recommendation

Interview responses:
{all_qa}

{f'Additional deal data: sector={deal.get("sector")}, DSCR={deal.get("dscr")}, grade={deal.get("credit_grade")}' if deal else ''}

Write in JPMorgan credit committee format. Direct, analytical, no hedging.
Lead with the conclusion. Numbers are authority."""

        return complete(
            "You are a senior credit underwriter at NEST Advisors writing an institutional credit memo.",
            prompt,
            max_tokens=4096,
        )

    def completion_status(self, answers: dict) -> dict:
        """Show % complete across all sections."""
        total = 0
        answered = 0
        by_section = {}

        for section in INTERVIEW_SECTIONS:
            section_total = len(section["questions"])
            section_answered = sum(1 for q in section["questions"] if q["id"] in answers)
            total += section_total
            answered += section_answered
            by_section[section["id"]] = {
                "title": section["title"],
                "total": section_total,
                "answered": section_answered,
                "pct": round(section_answered / section_total * 100) if section_total else 0,
            }

        return {
            "total_questions": total,
            "answered": answered,
            "pct": round(answered / total * 100) if total else 0,
            "by_section": by_section,
            "ready_for_memo": answered >= total * 0.75,  # 75% minimum for memo generation
        }
