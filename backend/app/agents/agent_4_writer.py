"""
Foedus — Agent 4: Writer
Generates professional tender proposals in Markdown.
"""

from app.agents.prompts import WRITER_PROMPT, WRITER_SYSTEM
from app.agents.state import AgentState
from app.services.llm_service import llm_service
from app.utils.helpers import format_inr
from app.utils.logger import logger


async def writer_node(state: AgentState) -> dict:
    """
    Agent 4: Proposal writer.

    Generates a 2000-3000 word professional proposal with:
    - Cover letter
    - Technical approach
    - Past experience
    - Compliance declaration
    - Company differentiators

    If this is a revision (from Agent 5 feedback), incorporates revision notes.
    Updates progress to 85%
    """
    logger.info("✍️  Agent 4: Writer starting...")

    company = state.get("company_profile", {})
    metadata = state.get("tender_metadata", {})
    match = state.get("match_result", {})
    audit = state.get("audit_result", {})
    risk = state.get("risk_result", {})
    tender_text = state.get("tender_text", "")

    revision_count = state.get("revision_count", 0)
    review = state.get("review_result", {})

    # Build compliance summary
    compliance_lines = []
    for item in audit.get("compliance_items", []):
        icon = {"met": "✅", "partial": "⚠️", "missing": "❌"}.get(item.get("status"), "❓")
        compliance_lines.append(f"{icon} {item.get('criterion', 'Unknown')} — {item.get('status', '?')}")
    compliance_summary = "\n".join(compliance_lines) or "No compliance data available"

    # Revision notes from reviewer
    revision_section = ""
    if revision_count > 0 and review:
        revision_section = f"""
REVISION #{revision_count} — Address the following feedback from the reviewer:
Score: {review.get('overall_score', 'N/A')}/10
Weaknesses: {', '.join(review.get('weaknesses', []))}
Notes: {review.get('revision_notes', 'No specific notes')}
"""

    prompt = WRITER_PROMPT.format(
        tender_title=state.get("tender_title", ""),
        tender_department=metadata.get("department", "Not specified"),
        tender_text_preview=tender_text[:3000],
        company_name=company.get("name", ""),
        company_description=company.get("description", ""),
        company_experience=company.get("years_experience", "N/A"),
        company_turnover=format_inr(company.get("turnover_lakh")),
        company_certs=", ".join(company.get("iso_certs", [])) or "None specified",
        company_projects=company.get("past_projects", "Not provided"),
        match_score=f"{match.get('overall_score', 0):.0%}",
        match_reasons=", ".join(match.get("match_reasons", [])),
        compliance_summary=compliance_summary,
        win_probability=f"{risk.get('win_probability', 0):.0%}",
        bid_strategy=risk.get("bid_strategy", "Standard bid approach"),
        revision_notes=revision_section,
    )

    try:
        proposal = await llm_service.call_plain(
            prompt=prompt,
            system_instruction=WRITER_SYSTEM,
            temperature=0.5,  # Slightly creative for writing
            max_output_tokens=8192,
        )
    except Exception as e:
        logger.error(f"Agent 4 failed: {e}")
        proposal = f"# Proposal for {state.get('tender_title', 'Tender')}\n\n_Proposal generation failed. Please try again._"

    word_count = len(proposal.split())
    logger.info(f"   ✅ Writer done — {word_count} words (revision #{revision_count})")

    return {
        "proposal_draft": proposal,
        "current_agent": "writer",
        "progress_pct": 85,
    }
