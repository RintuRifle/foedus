"""
Foedus — Agent 5: Reviewer
Self-critique loop — reviews proposal and either approves or sends back for revision.
"""

from app.agents.prompts import REVIEWER_PROMPT, REVIEWER_SYSTEM
from app.agents.schemas import ReviewResult
from app.agents.state import AgentState
from app.services.llm_service import llm_service
from app.utils.logger import logger

MAX_REVISIONS = 2


async def reviewer_node(state: AgentState) -> dict:
    """
    Agent 5: Proposal reviewer and quality gate.

    - Scores proposal on completeness, accuracy, professionalism (1-10)
    - If overall_score >= 7: approves → pipeline ends
    - If overall_score < 7 and revisions < MAX_REVISIONS: sends back to Writer
    - Updates progress to 95% (final step before completion)
    """
    logger.info("🔎 Agent 5: Reviewer starting...")

    company = state.get("company_profile", {})
    tender_text = state.get("tender_text", "")
    proposal = state.get("proposal_draft", "")
    audit = state.get("audit_result", {})

    # Build compliance summary for reviewer context
    compliance_lines = []
    for item in audit.get("compliance_items", []):
        status = item.get("status", "?")
        compliance_lines.append(f"[{status.upper()}] {item.get('criterion', '')}")
    compliance_summary = "\n".join(compliance_lines) or "No compliance data"

    prompt = REVIEWER_PROMPT.format(
        tender_text_preview=tender_text[:2000],
        company_name=company.get("name", ""),
        company_sectors=", ".join(company.get("sector", [])),
        proposal_draft=proposal,
        compliance_summary=compliance_summary,
    )

    try:
        result: ReviewResult = await llm_service.call(
            prompt=prompt,
            system_instruction=REVIEWER_SYSTEM,
            response_schema=ReviewResult,
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"Agent 5 failed: {e}")
        # Auto-approve on failure to prevent infinite loops
        result = ReviewResult(
            approved=True,
            overall_score=7,
            final_verdict="Auto-approved due to review error",
        )

    revision_count = state.get("revision_count", 0)

    # Decide: approve or revise
    if result.approved or result.overall_score >= 7:
        logger.info(f"   ✅ Reviewer APPROVED — score={result.overall_score}/10")
        return {
            "review_result": result.model_dump(),
            "final_proposal": proposal,
            "current_agent": "reviewer",
            "progress_pct": 100,
            "revision_count": revision_count,
        }
    elif revision_count >= MAX_REVISIONS:
        logger.info(f"   ⚠️  Max revisions ({MAX_REVISIONS}) reached — auto-approving")
        result.approved = True
        result.final_verdict = f"Approved after {MAX_REVISIONS} revision attempts"
        return {
            "review_result": result.model_dump(),
            "final_proposal": proposal,
            "current_agent": "reviewer",
            "progress_pct": 100,
            "revision_count": revision_count,
        }
    else:
        logger.info(f"   🔄 Reviewer REJECTED — score={result.overall_score}/10, sending back to writer")
        return {
            "review_result": result.model_dump(),
            "current_agent": "reviewer",
            "progress_pct": 80,  # Step back for revision
            "revision_count": revision_count + 1,
        }
