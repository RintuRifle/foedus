"""
TenderAI — OCR & PDF Text Extraction Service
Primary: PyMuPDF for text-based PDFs
Fallback: Gemini Vision API for scanned/image PDFs
"""

import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import google.generativeai as genai

from app.config import settings
from app.utils.helpers import clean_text
from app.utils.logger import logger

class OCRService:
    """
    Extracts text content from PDF documents.

    Strategy:
    1. Try PyMuPDF text extraction first (fast, free, works for text PDFs)
    2. If extracted text is too short (<100 chars), assume scanned PDF
    3. Fall back to Gemini Vision API for scanned/image PDFs
    """

    MIN_TEXT_THRESHOLD = 100  # chars — below this, PDF is likely scanned

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.gemini_model = None
            logger.warning("GEMINI_API_KEY not set — OCR fallback unavailable")

    async def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file.
        Tries PyMuPDF first, falls back to Gemini Vision for scanned PDFs.
        """
        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"PDF not found: {pdf_path}")
            return ""

        logger.info(f"📄 Extracting text from: {path.name}")

        # Step 1: Try PyMuPDF
        text = self._extract_with_pymupdf(str(path))

        if len(text.strip()) >= self.MIN_TEXT_THRESHOLD:
            logger.info(f"   ✅ PyMuPDF extracted {len(text)} chars")
            return clean_text(text)

        # Step 2: Fallback to Gemini Vision
        logger.info(f"   ⚠️ PyMuPDF got only {len(text)} chars — trying Gemini Vision...")
        gemini_text = await self._extract_with_gemini_vision(str(path))

        if gemini_text:
            logger.info(f"   ✅ Gemini Vision extracted {len(gemini_text)} chars")
            return clean_text(gemini_text)

        # Return whatever we got
        logger.warning(f"   ❌ Could not extract meaningful text from {path.name}")
        return clean_text(text)

    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF (fast, free)."""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            doc.close()
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return ""

    async def _extract_with_gemini_vision(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from scanned PDF using Gemini 1.5 Flash vision.
        Uploads the PDF and asks Gemini to extract all text.
        """
        if not self.gemini_model:
            logger.warning("Gemini model not available for vision OCR")
            return None

        try:
            # Upload the PDF to Gemini
            uploaded_file = genai.upload_file(pdf_path)

            prompt = """Extract ALL text content from this PDF document.
            Maintain the original structure including:
            - Headers and subheaders
            - Numbered lists and bullet points
            - Table data (format as plain text tables)
            - All eligibility criteria and requirements
            - Financial details, dates, and deadlines

            Return ONLY the extracted text, no commentary."""

            response = self.gemini_model.generate_content(
                [prompt, uploaded_file],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 8192,
                },
            )

            # Clean up uploaded file
            try:
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass

            return response.text if response.text else None

        except Exception as e:
            logger.error(f"Gemini Vision OCR failed: {e}")
            return None

    def detect_pdf_type(self, pdf_path: str) -> str:
        """
        Detect if PDF is text-based, scanned (image), or hybrid.
        Used by Agent 0 (Preprocessor) to route processing.
        """
        try:
            doc = fitz.open(pdf_path)
            text_pages = 0
            image_pages = 0

            for page in doc:
                text = page.get_text("text").strip()
                images = page.get_images()

                if len(text) > 50:
                    text_pages += 1
                if len(images) > 0 and len(text) < 50:
                    image_pages += 1

            doc.close()

            total = text_pages + image_pages
            if total == 0:
                return "empty"
            if image_pages == 0:
                return "text"
            if text_pages == 0:
                return "scanned"
            return "hybrid"

        except Exception as e:
            logger.error(f"PDF type detection failed: {e}")
            return "unknown"

# Singleton
ocr_service = OCRService()
