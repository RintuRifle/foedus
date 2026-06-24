"""
Foedus — Agent 2: Auditor
Cross-checks every eligibility criterion against company documents.
Produces the compliance matrix.
"""

from app.agents.prompts import AUDITOR_PROMPT, AUDITOR_SYSTEM
from app.agents.schemas import AuditResult
from app.agents.state import AgentState
from app.services.llm_service import llm_service
from app.utils.helpers import format_inr
from app.utils.logger import logger


async def auditor_node(state: AgentState) -> dict:
    """
    Agent 2: Eligibility audit — the most critical agent.

    - Extracts ALL eligibility criteria from tender text
    - Cross-checks each against company profile + documents
    - Status per criterion: met | partial | missing
    - Identifies missing documents and critical gaps

    Updates progress to 50%
    """
    logger.info("📋 Agent 2: Auditor starting...")

    company = state.get("company_profile", {})
    tender_text = state.get("tender_text", "")
    company_docs = state.get("company_documents", [])

    docs_summary = "\n".join(
        f"- {doc[:200]}..." if len(doc) > 200 else f"- {doc}"
        for doc in company_docs[:10]
    ) if company_docs else "No documents uploaded"

    prompt = AUDITOR_PROMPT.format(
        tender_text=tender_text[:6000],  # More text for thorough audit
        company_name=company.get("name", ""),
        company_turnover=company.get("turnover_lakh", "N/A"),
        company_experience=company.get("years_experience", "N/A"),
        company_location=f"{company.get('location_city', '')}, {company.get('location_state', '')}",
        company_gst=company.get("gst_number", "Not provided"),
        company_pan=company.get("pan_number", "Not provided"),
        company_certs=", ".join(company.get("iso_certs", [])) or "None",
        company_projects=company.get("past_projects", "Not provided"),
        company_documents=docs_summary,
    )

    try:
        result: AuditResult = await llm_service.call(
            prompt=prompt,
            system_instruction=AUDITOR_SYSTEM,
            response_schema=AuditResult,
            temperature=0.1,  # Low temp for accuracy
            max_output_tokens=4096,
        )
        # Recount from actual items
        result.met_count = sum(1 for i in result.compliance_items if i.status == "met")
        result.partial_count = sum(1 for i in result.compliance_items if i.status == "partial")
        result.missing_count = sum(1 for i in result.compliance_items if i.status == "missing")

    except Exception as e:
        logger.error(f"Agent 2 failed: {e}")
        result = AuditResult(
            overall_status="partially_eligible",
            summary="Audit could not be completed — manual review required",
        )

    logger.info(
        f"   ✅ Auditor done — {result.overall_status} "
        f"(met={result.met_count}, partial={result.partial_count}, missing={result.missing_count})"
    )

    return {
        "audit_result": result.model_dump(),
        "current_agent": "auditor",
        "progress_pct": 50,
    }
