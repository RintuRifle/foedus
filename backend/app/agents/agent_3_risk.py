"""
Foedus — Agent 3: Risk Assessor
Estimates win probability and competitive landscape.
"""

from app.agents.prompts import RISK_PROMPT, RISK_SYSTEM
from app.agents.schemas import RiskResult
from app.agents.state import AgentState
from app.services.llm_service import llm_service
from app.utils.helpers import format_inr
from app.utils.logger import logger


async def risk_node(state: AgentState) -> dict:
    """
    Agent 3: Strategic risk assessment.

    - Analyzes competitive landscape
    - Estimates win probability based on match + audit results
    - Identifies specific risk factors
    - Provides bid/skip recommendation with strategy

    Updates progress to 70%
    """
    logger.info("⚠️  Agent 3: Risk Assessor starting...")

    metadata = state.get("tender_metadata", {})
    match = state.get("match_result", {})
    audit = state.get("audit_result", {})
    company = state.get("company_profile", {})

    # Build strengths from match reasons
    company_strengths = "\n".join(
        f"- {r}" for r in match.get("match_reasons", [])
    ) or "No specific strengths identified"

    # Build gaps from audit
    audit_gaps = "\n".join(
        f"- {g}" for g in audit.get("critical_gaps", [])
    )
    if audit.get("missing_documents"):
        audit_gaps += "\nMissing documents:\n" + "\n".join(
            f"- {d}" for d in audit["missing_documents"]
        )
    if not audit_gaps:
        audit_gaps = "No critical gaps identified"

    total_criteria = (
        audit.get("met_count", 0) +
        audit.get("partial_count", 0) +
        audit.get("missing_count", 0)
    )

    prompt = RISK_PROMPT.format(
        tender_title=state.get("tender_title", ""),
        tender_value=format_inr(metadata.get("value_lakh")),
        tender_emd=format_inr(metadata.get("emd_amount")),
        tender_sector=", ".join(metadata.get("sector", [])),
        tender_source=metadata.get("source", "unknown"),
        match_score=f"{match.get('overall_score', 0):.2f}",
        eligibility_status=audit.get("overall_status", "unknown"),
        met_count=audit.get("met_count", 0),
        total_criteria=total_criteria,
        company_strengths=company_strengths,
        audit_gaps=audit_gaps,
    )

    try:
        result: RiskResult = await llm_service.call(
            prompt=prompt,
            system_instruction=RISK_SYSTEM,
            response_schema=RiskResult,
            temperature=0.3,
        )
    except Exception as e:
        logger.error(f"Agent 3 failed: {e}")
        result = RiskResult(
            win_probability=0.3,
            competition_level="medium",
            recommendation="conditional_bid",
            risk_factors=["Risk assessment could not be completed"],
        )

    logger.info(
        f"   ✅ Risk done — win_prob={result.win_probability:.2f}, "
        f"competition={result.competition_level}, rec={result.recommendation}"
    )

    return {
        "risk_result": result.model_dump(),
        "current_agent": "risk_assessor",
        "progress_pct": 70,
    }
