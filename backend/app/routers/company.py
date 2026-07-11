"""
Foedus — Company Router
Company profile CRUD, document vault, and ✨ Magic Onboarding:
upload a brochure PDF → AI parses it → profile auto-filled.
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.company import Company, CompanyDocument
from app.models.user import User
from app.schemas.company import (
    BrochureParseResponse,
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    DocumentUploadResponse,
)
from app.services.llm_service import llm_service
from app.services.ocr_service import ocr_service
from app.utils.logger import logger

router = APIRouter(prefix="/company", tags=["Company"])

UPLOAD_DIR = "./data/uploads"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

BROCHURE_PARSE_SYSTEM = """You are an expert at reading Indian SME company brochures, \
profiles, and capability statements. Extract structured company information.

Rules:
- Extract ONLY what is actually stated. Never invent numbers.
- turnover_lakh: annual turnover converted to Lakhs INR (1 Cr = 100 Lakh).
- sector: lowercase tags like ["solar", "civil", "electrical", "it", "pharma"].
- past_projects: 3-6 sentence summary of notable projects with values/clients if given.
- keywords: 8-15 search keywords describing capabilities.
- confidence: how confident you are overall (0-1). Low text quality → low confidence.
- If a field is not present in the text, leave it null."""


async def _get_company(user: User, db: AsyncSession) -> Company | None:
    result = await db.execute(select(Company).where(Company.user_id == user.id))
    return result.scalar_one_or_none()


async def _save_upload(file: UploadFile, subdir: str) -> tuple[str, int]:
    """Persist an uploaded file to local storage. Returns (path, size)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 15 MB)")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="File is not a valid PDF")

    directory = os.path.join(UPLOAD_DIR, subdir)
    os.makedirs(directory, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.pdf"
    path = os.path.join(directory, safe_name)
    with open(path, "wb") as f:
        f.write(content)
    return path, len(content)


@router.get("", response_model=CompanyResponse)
async def get_my_company(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    if company is None:
        raise HTTPException(status_code=404, detail="Company profile not set up yet")
    return company


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if await _get_company(current_user, db):
        raise HTTPException(
            status_code=409, detail="Company already exists. Use PATCH to update."
        )
    company = Company(user_id=current_user.id, **body.model_dump(exclude_none=True))
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.patch("", response_model=CompanyResponse)
async def update_company(
    body: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    if company is None:
        raise HTTPException(status_code=404, detail="Company profile not set up yet")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(company, field, value)
    await db.commit()
    await db.refresh(company)
    return company


@router.post("/onboard-brochure", response_model=BrochureParseResponse)
async def magic_onboarding(
    file: UploadFile = File(..., description="Company brochure / profile PDF"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✨ Magic Onboarding.
    Upload a company brochure PDF — the AI reads it and auto-fills
    the company profile (created or updated in place). The parsed
    fields are returned so the frontend can show a review screen.
    """
    path, _size = await _save_upload(file, "brochures")

    # 1. Extract text (PyMuPDF → Gemini Vision fallback for scanned PDFs)
    text = await ocr_service.extract_text(path)
    if not text or len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Couldn't read enough text from this PDF. Try a text-based brochure.",
        )

    # 2. LLM structured parse
    try:
        parsed: BrochureParseResponse = await llm_service.call(
            prompt=f"Extract company information from this brochure:\n\n{text[:60000]}",
            system_instruction=BROCHURE_PARSE_SYSTEM,
            response_schema=BrochureParseResponse,
            temperature=0.1,
        )
    except Exception as e:
        logger.error(f"Brochure parse failed: {e}")
        raise HTTPException(status_code=502, detail="AI parsing failed. Try again.")

    # 3. Upsert company profile with parsed fields
    company = await _get_company(current_user, db)
    fields = parsed.model_dump(exclude_none=True, exclude={"confidence"})
    if company is None:
        company = Company(
            user_id=current_user.id,
            name=fields.pop("name", None) or "My Company",
            **fields,
        )
        db.add(company)
    else:
        for field, value in fields.items():
            setattr(company, field, value)
    company.brochure_url = path
    await db.commit()

    logger.info(
        f"✨ Magic onboarding: {current_user.email} → "
        f"'{company.name}' (confidence {parsed.confidence:.0%})"
    )
    return parsed


@router.get("/documents", response_model=list[DocumentUploadResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    if company is None:
        return []
    result = await db.execute(
        select(CompanyDocument).where(CompanyDocument.company_id == company.id)
    )
    return result.scalars().all()


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    doc_type: str,
    file: UploadFile = File(...),
    year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Document vault upload (audit reports, GST cert, ISO certs...).
    Text is extracted immediately so the Auditor agent can use it.
    """
    allowed = {
        "audit_report", "gst_cert", "pan", "iso_cert",
        "portfolio", "balance_sheet", "experience_cert",
    }
    if doc_type not in allowed:
        raise HTTPException(
            status_code=422, detail=f"Invalid doc_type. Allowed: {sorted(allowed)}"
        )

    company = await _get_company(current_user, db)
    if company is None:
        raise HTTPException(
            status_code=400, detail="Set up your company profile first"
        )

    path, size = await _save_upload(file, "documents")
    parsed_text = None
    try:
        parsed_text = await ocr_service.extract_text(path)
    except Exception as e:
        logger.warning(f"Document OCR failed (stored anyway): {e}")

    doc = CompanyDocument(
        company_id=company.id,
        doc_type=doc_type,
        file_url=path,
        file_name=file.filename,
        file_size_bytes=size,
        year=year,
        parsed_text=parsed_text,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(current_user, db)
    doc = await db.get(CompanyDocument, doc_id) if company else None
    if doc is None or doc.company_id != company.id:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
