"""
Foedus — Agent 0: Preprocessor
Analyzes tender document structure before deep processing.
Detects PDF type, language, and key sections.
"""

from app.agents.prompts import PREPROCESSOR_PROMPT, PREPROCESSOR_SYSTEM
from app.agents.schemas import PreprocessorOutput
from app.agents.state import AgentState
from app.services.llm_service import llm_service
from app.services.ocr_service import ocr_service
from app.utils.logger import logger


async def preprocessor_node(state: AgentState) -> dict:
    """
    Agent 0: Analyze the tender document structure.

    - Detects PDF type (text/scanned/hybrid)
    - Identifies key sections (eligibility, scope, financial, timeline)
    - Generates a quick summary for downstream agents
    - Updates progress to 15%
    """
    logger.info("🔍 Agent 0: Preprocessor starting...")

    tender_text = state.get("tender_text", "")
    tender_title = state.get("tender_title", "Unknown Tender")
    metadata = state.get("tender_metadata", {})

    # Detect PDF type if local path exists
    pdf_type = "text"
    local_pdf = metadata.get("local_pdf_path")
    if local_pdf:
        try:
            pdf_type = ocr_service.detect_pdf_type(local_pdf)
        except Exception:
            pdf_type = "unknown"

    # Prepare preview for LLM (first 3000 chars to save tokens)
    text_preview = tender_text[:3000] if tender_text else "No text available"

    prompt = PREPROCESSOR_PROMPT.format(
        tender_title=tender_title,
        source=metadata.get("source", "unknown"),
        tender_text_preview=text_preview,
    )

    try:
        result: PreprocessorOutput = await llm_service.call(
            prompt=prompt,
            system_instruction=PREPROCESSOR_SYSTEM,
            response_schema=PreprocessorOutput,
            temperature=0.1,
            max_output_tokens=1024,
        )
        result.pdf_type = pdf_type

    except Exception as e:
        logger.error(f"Agent 0 failed: {e}")
        result = PreprocessorOutput(
            pdf_type=pdf_type,
            tender_summary=f"Tender: {tender_title}",
        )

    logger.info(f"   ✅ Preprocessor done — type={result.pdf_type}, sections={len(result.key_sections)}")

    return {
        "preprocessor_result": result.model_dump(),
        "current_agent": "preprocessor",
        "progress_pct": 15,
    }
