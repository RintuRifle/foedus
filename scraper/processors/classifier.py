"""
Foedus — Tender Classifier
Uses Gemini to classify tenders by sector from their title/description.
"""

from typing import List, Optional

import google.generativeai as genai
from loguru import logger

from app.config import settings

class TenderClassifier:
    """
    AI-powered tender classification.
    Tags tenders by sector based on title and description.
    Uses Gemini 1.5 Flash (fast, free tier friendly).
    """

    VALID_SECTORS = [
        "solar", "renewable_energy", "electrical", "civil",
        "construction", "road", "bridge", "it", "software",
        "telecom", "pharma", "medical", "water", "sanitation",
        "agriculture", "defense", "transport", "education",
        "housing", "mining", "oil_gas", "textile", "food",
        "consulting", "security", "other",
    ]

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY not set — classifier will use keyword fallback")

    async def classify(self, title: str, description: str = "") -> List[str]:
        """
        Classify a tender into one or more sectors.
        Uses LLM if available, falls back to keyword matching.
        """
        if self.model:
            return await self._classify_with_llm(title, description)
        return self._classify_with_keywords(title, description)

    async def _classify_with_llm(self, title: str, description: str) -> List[str]:
        """Use Gemini to classify tender sector."""
        try:
            prompt = f"""Classify this Indian government tender into 1-3 sectors.

VALID SECTORS: {', '.join(self.VALID_SECTORS)}

TENDER TITLE: {title}
DESCRIPTION: {description[:500] if description else 'N/A'}

Return ONLY a comma-separated list of matching sectors, nothing else.
Example: solar, electrical, construction"""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 50,
                },
            )

            if response.text:
                sectors = [s.strip().lower() for s in response.text.split(",")]
                # Validate against known sectors
                valid = [s for s in sectors if s in self.VALID_SECTORS]
                return valid if valid else ["other"]

        except Exception as e:
            logger.warning(f"   LLM classification failed: {e}")

        return self._classify_with_keywords(title, description)

    def _classify_with_keywords(self, title: str, description: str) -> List[str]:
        """Fallback: classify using keyword matching."""
        text = f"{title} {description}".lower()
        sectors = []

        keyword_map = {
            "solar": ["solar", "photovoltaic", "pv module", "solar panel", "solar plant"],
            "renewable_energy": ["wind energy", "biomass", "renewable", "green energy"],
            "electrical": ["electrical", "substation", "transformer", "transmission line", "switchgear"],
            "civil": ["civil work", "building construction", "civil engineering"],
            "construction": ["construction", "building", "erection", "fabrication"],
            "road": ["road", "highway", "national highway", "nh-", "flyover", "overpass"],
            "it": ["software", "it service", "computer", "server", "networking", "data center", "ict"],
            "telecom": ["telecom", "optical fiber", "ofn", "mobile tower", "4g", "5g"],
            "pharma": ["medicine", "pharmaceutical", "drug", "medical equipment", "hospital"],
            "water": ["water supply", "water treatment", "pipeline", "sewage", "drinking water"],
            "agriculture": ["agriculture", "irrigation", "farming", "fertilizer", "seed"],
            "defense": ["army", "navy", "air force", "defense", "defence", "military", "ordnance"],
            "education": ["school", "university", "college", "education", "training"],
        }

        for sector, keywords in keyword_map.items():
            if any(kw in text for kw in keywords):
                sectors.append(sector)

        return sectors if sectors else ["other"]

# Singleton
classifier = TenderClassifier()
