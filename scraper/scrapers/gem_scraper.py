"""
TenderAI — GeM (Government e-Marketplace) Scraper
gem.gov.in — India's largest public procurement platform (₹2 lakh crore+ GMV).
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from scraper.scrapers.base_scraper import BaseScraper, ScrapedTender

class GeMScraper(BaseScraper):
    """
    Scrapes bid/tender listings from GeM (Government e-Marketplace).

    GeM has a semi-public API that returns JSON data for bid listings.
    This is much more reliable than HTML scraping.
    """

    def __init__(self, max_pages: int = 5):
        super().__init__(
            source_name="gem",
            base_url="https://bidplus.gem.gov.in/all-bids",
            max_pages=max_pages,
            request_delay=2.0,
        )
        self.api_url = "https://bidplus.gem.gov.in/bidlists"

    async def fetch_tenders(self) -> List[ScrapedTender]:
        """Fetch active bids from GeM portal."""
        tenders = []

        for page in range(1, self.max_pages + 1):
            logger.info(f"   📄 Fetching GeM bids page {page}/{self.max_pages}...")

            page_tenders = await self._fetch_bid_page(page)
            if not page_tenders:
                break

            tenders.extend(page_tenders)
            await self._rate_limit_delay()

        return tenders

    async def _fetch_bid_page(self, page: int) -> List[ScrapedTender]:
        """Fetch a single page of bids from GeM."""
        # GeM uses a paginated listing page
        url = f"{self.base_url}"
        params = {"page_no": page}

        html = await self._fetch_page(url, params=params)
        if not html:
            return []

        return self._parse_bid_listing(html)

    def _parse_bid_listing(self, html: str) -> List[ScrapedTender]:
        """Parse GeM bid listing page."""
        from bs4 import BeautifulSoup

        tenders = []
        soup = BeautifulSoup(html, "lxml")

        # GeM renders bids in div-based cards
        bid_cards = soup.find_all("div", class_="bid-listing-item") or \
                    soup.find_all("div", class_="block") or \
                    soup.find_all("div", {"id": lambda x: x and x.startswith("bid")})

        if not bid_cards:
            # Fallback: try table-based layout
            bid_cards = soup.find_all("tr", class_="bid-row")

        for card in bid_cards:
            try:
                tender = self._parse_bid_card(card)
                if tender:
                    tenders.append(tender)
            except Exception as e:
                logger.debug(f"   Error parsing GeM bid card: {e}")
                continue

        return tenders

    def _parse_bid_card(self, card) -> Optional[ScrapedTender]:
        """Parse a single GeM bid card into ScrapedTender."""
        # Extract bid number
        bid_id_elem = card.find("span", class_="bid-no") or \
                      card.find(text=lambda t: t and "GEM" in str(t).upper())

        bid_id = None
        if bid_id_elem:
            bid_id = bid_id_elem.get_text(strip=True) if hasattr(bid_id_elem, 'get_text') else str(bid_id_elem).strip()

        # Extract title/description
        title_elem = card.find("span", class_="bid-title") or \
                     card.find("a", class_="bid-title") or \
                     card.find("p", class_="description")

        title = title_elem.get_text(strip=True) if title_elem else None
        if not title or len(title) < 5:
            return None

        # Extract organization
        org_elem = card.find("span", class_="org-name") or \
                   card.find("div", class_="ministry")
        organization = org_elem.get_text(strip=True) if org_elem else None

        # Extract value
        value_elem = card.find("span", class_="bid-value") or \
                     card.find(text=lambda t: t and "₹" in str(t))
        value_lakh = None
        if value_elem:
            value_text = value_elem.get_text(strip=True) if hasattr(value_elem, 'get_text') else str(value_elem)
            value_lakh = self._parse_gem_value(value_text)

        # Extract dates
        from app.utils.helpers import parse_date_flexible
        submission_date = None
        date_elems = card.find_all("span", class_="bid-date") or \
                     card.find_all(text=lambda t: t and "/" in str(t) and len(str(t)) < 15)
        for de in date_elems:
            text = de.get_text(strip=True) if hasattr(de, 'get_text') else str(de).strip()
            parsed = parse_date_flexible(text)
            if parsed:
                submission_date = parsed
                break

        # Extract PDF/document link
        pdf_url = None
        doc_link = card.find("a", href=lambda h: h and ("document" in h.lower() or ".pdf" in h.lower()))
        if doc_link:
            pdf_url = doc_link["href"]
            if not pdf_url.startswith("http"):
                pdf_url = f"https://bidplus.gem.gov.in{pdf_url}"

        return ScrapedTender(
            external_id=bid_id or f"gem-{hash(title) % 100000}",
            source="gem",
            title=title,
            organization=organization,
            value_lakh=value_lakh,
            submission_date=submission_date,
            pdf_url=pdf_url,
        )

    def _parse_gem_value(self, text: str) -> Optional[float]:
        """Parse GeM bid value string to Lakh INR."""
        import re
        if not text:
            return None

        # Remove ₹ and commas
        clean = text.replace("₹", "").replace(",", "").strip()

        match = re.search(r'([\d.]+)\s*(lakh|lac|cr|crore)?', clean.lower())
        if match:
            value = float(match.group(1))
            unit = match.group(2) or ""
            if "cr" in unit:
                return value * 100
            if "lakh" in unit or "lac" in unit:
                return value
            # Plain number — assume in Rs
            if value > 100000:
                return value / 100000
            return value
        return None
