"""
Foedus — Context Builder
Prepares the initial AgentState before the LangGraph pipeline runs.
Loads all data from PostgreSQL + Qdrant.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.models.company import Company, CompanyDocument
from app.models.tender import Tender
from app.services.embedding_service import embedding_service
from app.services.ocr_service import ocr_service
from app.services.vectorstore_service import vectorstore_service
from app.utils.logger import logger


async def build_context(
    tender_id: str,
    user_id: str,
    db: AsyncSession,
    job_id: Optional[str] = None,
) -> AgentState:
    """
    Load all data needed for the evaluation pipeline.

    1. Fetch tender from PostgreSQL
    2. Fetch company profile + documents
    3. Retrieve relevant chunks from Qdrant (RAG)
    4. Build the complete AgentState dict
    """
    logger.info(f"📦 Building context for tender={tender_id}, user={user_id}")

    # Load tender
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise ValueError(f"Tender {tender_id} not found")

    tender_metadata = {
        "source": tender.source,
        "sector": tender.sector or [],
        "state": tender.state,
        "department": tender.department,
        "organization": tender.organization,
        "value_lakh": float(tender.value_lakh) if tender.value_lakh else None,
        "emd_amount": float(tender.emd_amount) if tender.emd_amount else None,
        "tender_fee": float(tender.tender_fee) if tender.tender_fee else None,
        "submission_date": str(tender.submission_date) if tender.submission_date else None,
        "opening_date": str(tender.opening_date) if tender.opening_date else None,
        "local_pdf_path": tender.local_pdf_path,
        "external_id": tender.external_id,
    }

    # Load company profile
    result = await db.execute(
        select(Company).where(Company.user_id == user_id)
    )
    company = result.scalar_one_or_none()

    company_profile = {}
    if company:
        company_profile = {
            "name": company.name,
            "description": company.description or "",
            "sector": company.sector or [],
            "turnover_lakh": float(company.turnover_lakh) if company.turnover_lakh else None,
            "emp_count": company.emp_count,
            "years_experience": company.years_experience,
            "location_state": company.location_state or "",
            "location_city": company.location_city or "",
            "pan_number": company.pan_number or "",
            "gst_number": company.gst_number or "",
            "iso_certs": company.iso_certs or [],
            "past_projects": company.past_projects or "",
            "keywords": company.keywords or [],
        }

    # Load company documents (parsed text)
    company_documents = []
    if company:
        doc_result = await db.execute(
            select(CompanyDocument)
            .where(CompanyDocument.company_id == company.id)
            .where(CompanyDocument.parsed_text.isnot(None))
        )
        docs = doc_result.scalars().all()
        company_documents = [
            f"[{doc.doc_type}] {doc.parsed_text}" for doc in docs if doc.parsed_text
        ]

    # RAG: retrieve relevant chunks from Qdrant
    rag_context = []
    if tender.parsed_text and len(tender.parsed_text) > 100:
        try:
            # Create a query from company keywords + sector
            query_parts = []
            if company_profile.get("sector"):
                query_parts.extend(company_profile["sector"])
            if company_profile.get("keywords"):
                query_parts.extend(company_profile["keywords"][:5])
            query_parts.append(tender.title)

            query_text = " ".join(query_parts)
            query_vector = embedding_service.embed_text(query_text)

            results = vectorstore_service.search(
                query_vector=query_vector,
                tender_id=str(tender.id),
                limit=5,
                score_threshold=0.3,
            )
            rag_context = [r["text"] for r in results if r.get("text")]
            logger.info(f"   RAG: retrieved {len(rag_context)} relevant chunks")
        except Exception as e:
            logger.warning(f"   RAG retrieval failed (non-fatal): {e}")

    # ── Edge case: no/garbage parsed text but PDF on disk ─────
    # (scanned PDFs sometimes yield <100 chars from PyMuPDF; the OCR
    #  service falls back to Gemini Vision for image-based pages)
    tender_text = tender.parsed_text or ""
    if len(tender_text.strip()) < 100 and tender.local_pdf_path:
        logger.warning(
            f"   Tender text too thin ({len(tender_text)} chars) — re-running OCR on {tender.local_pdf_path}"
        )
        try:
            recovered = await ocr_service.extract_text(tender.local_pdf_path)
            if recovered and len(recovered.strip()) > len(tender_text.strip()):
                tender_text = recovered
                tender.parsed_text = recovered  # persist for next time
                await db.commit()
                logger.info(f"   ✅ OCR recovery: {len(recovered)} chars extracted")
        except Exception as e:
            logger.warning(f"   OCR recovery failed (non-fatal): {e}")
    if not tender_text.strip():
        tender_text = tender.description or tender.title

    state: AgentState = {
        "tender_id": str(tender.id),
        "user_id": str(user_id),
        "tender_text": tender_text,
        "tender_title": tender.title,
        "tender_metadata": tender_metadata,
        "company_profile": company_profile,
        "company_documents": company_documents,
        "rag_context": rag_context,
        "current_agent": "context_builder",
        "progress_pct": 5,
        "revision_count": 0,
        "error": None,
    }

    if job_id:
        state["job_id"] = job_id

    logger.info(
        f"   ✅ Context built — tender_text={len(state['tender_text'])} chars, "
        f"company_docs={len(company_documents)}, rag_chunks={len(rag_context)}"
    )
    return state
