"""
Foedus — Agent 1: Matchmaker
Calculates multi-criteria match score between company profile and tender.
RAG-enhanced with Qdrant context.
"""

from app.agents.prompts import MATCHMAKER_PROMPT, MATCHMAKER_SYSTEM
from app.agents.schemas import MatchResult
from app.agents.state import AgentState
from app.services.llm_service import llm_service
from app.utils.helpers import format_inr
from app.utils.logger import logger


async def matchmaker_node(state: AgentState) -> dict:
    """
    Agent 1: Score how well the company matches this tender.

    Multi-criteria scoring:
    - Sector alignment
    - Budget/turnover fit
    - Location relevance
    - Experience years
    - Certifications

    Updates progress to 30%
    """
    logger.info("🎯 Agent 1: Matchmaker starting...")

    company = state.get("company_profile", {})
    metadata = state.get("tender_metadata", {})
    tender_text = state.get("tender_text", "")
    rag_chunks = state.get("rag_context", [])

    rag_text = "\n---\n".join(rag_chunks[:5]) if rag_chunks else "No additional context available"

    prompt = MATCHMAKER_PROMPT.format(
        tender_title=state.get("tender_title", ""),
        tender_sector=", ".join(metadata.get("sector", [])),
        tender_value=format_inr(metadata.get("value_lakh")),
        tender_state=metadata.get("state", "Not specified"),
        tender_department=metadata.get("department", "Not specified"),
        tender_text_preview=tender_text[:2000],
        company_name=company.get("name", ""),
        company_sectors=", ".join(company.get("sector", [])),
        company_turnover=format_inr(company.get("turnover_lakh")),
        company_experience=company.get("years_experience", "N/A"),
        company_location=f"{company.get('location_city', '')}, {company.get('location_state', '')}",
        company_certs=", ".join(company.get("iso_certs", [])),
        company_projects=company.get("past_projects", "Not provided"),
        rag_context=rag_text,
    )

    try:
        result: MatchResult = await llm_service.call(
            prompt=prompt,
            system_instruction=MATCHMAKER_SYSTEM,
            response_schema=MatchResult,
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"Agent 1 failed: {e}")
        result = MatchResult(
            overall_score=0.5,
            recommendation="evaluate",
            match_reasons=["Unable to fully assess — manual review recommended"],
        )

    logger.info(f"   ✅ Matchmaker done — score={result.overall_score:.2f}, rec={result.recommendation}")

    return {
        "match_result": result.model_dump(),
        "current_agent": "matchmaker",
        "progress_pct": 30,
    }
