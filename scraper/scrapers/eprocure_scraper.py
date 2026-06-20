"""
Foedus — eProcure.gov.in Scraper
Central Public Procurement Portal — India's largest tender portal.
"""

import re
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from scraper.scrapers.base_scraper import BaseScraper, ScrapedTender

class EProcureScraper(BaseScraper):
    """
    Scrapes active tenders from eprocure.gov.in.

    The portal uses server-rendered HTML tables with pagination.
    We scrape the active tenders listing page and extract:
    - Tender ID, Title, Organization, Value
    - Submission deadline, Opening date
    - PDF document links
    """

    def __init__(self, max_pages: int = 5):
        super().__init__(
            source_name="eprocure",
            base_url="https://eprocure.gov.in/eprocure/app",
            max_pages=max_pages,
            request_delay=3.0,  # Be polite with gov sites
        )

    async def fetch_tenders(self) -> List[ScrapedTender]:
        """Fetch active tenders from eProcure portal."""
        tenders = []

        for page in range(1, self.max_pages + 1):
            logger.info(f"   📄 Fetching page {page}/{self.max_pages}...")

            html = await self._fetch_listing_page(page)
            if not html:
                logger.warning(f"   Could not fetch page {page}")
                break

            page_tenders = self._parse_listing_page(html)
            if not page_tenders:
                logger.info(f"   No more tenders on page {page}")
                break

            tenders.extend(page_tenders)
            await self._rate_limit_delay()

        return tenders

    async def _fetch_listing_page(self, page: int) -> Optional[str]:
        """Fetch a single listing page from eProcure."""
        # eProcure uses a search endpoint with POST or GET params
        url = f"{self.base_url}"
        params = {
            "page": page,
            "service": "page",
            "searchType": "active",
        }
        return await self._fetch_page(url, params=params)

    def _parse_listing_page(self, html: str) -> List[ScrapedTender]:
        """Parse HTML listing page and extract tender data."""
        tenders = []
        soup = BeautifulSoup(html, "lxml")

        # eProcure typically renders tenders in table rows
        # The exact selectors may need adjustment based on current page structure
        table = soup.find("table", {"id": "table"}) or soup.find("table", class_="list_table")
        if not table:
            # Try finding any data table
            tables = soup.find_all("table")
            for t in tables:
                rows = t.find_all("tr")
                if len(rows) > 2:  # Has data rows
                    table = t
                    break

        if not table:
            logger.debug("   No data table found on page")
            return tenders

        rows = table.find_all("tr")[1:]  # Skip header

        for row in rows:
            try:
                tender = self._parse_tender_row(row)
                if tender:
                    tenders.append(tender)
            except Exception as e:
                logger.debug(f"   Error parsing row: {e}")
                continue

        return tenders

    def _parse_tender_row(self, row) -> Optional[ScrapedTender]:
        """Parse a single table row into a ScrapedTender."""
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        # Extract text from cells
        cell_texts = [cell.get_text(strip=True) for cell in cells]

        # Try to find tender ID and title
        tender_id = cell_texts[0] if cell_texts[0] else None
        title = cell_texts[1] if len(cell_texts) > 1 else None

        if not title or len(title) < 10:
            return None

        # Extract PDF link if available
        pdf_link = None
        for cell in cells:
            link = cell.find("a", href=True)
            if link and (".pdf" in link["href"].lower() or "document" in link["href"].lower()):
                href = link["href"]
                if not href.startswith("http"):
                    href = f"https://eprocure.gov.in{href}"
                pdf_link = href
                break

        # Try to extract value from text
        value_lakh = self._extract_value(cell_texts)

        # Try to parse dates
        from app.utils.helpers import parse_date_flexible
        submission_date = None
        opening_date = None
        for text in cell_texts:
            parsed = parse_date_flexible(text)
            if parsed:
                if submission_date is None:
                    submission_date = parsed
                else:
                    opening_date = parsed

        # Extract organization
        organization = cell_texts[2] if len(cell_texts) > 2 else None

        return ScrapedTender(
            external_id=tender_id or f"eprocure-{hash(title) % 100000}",
            source="eprocure",
            title=title,
            organization=organization,
            value_lakh=value_lakh,
            submission_date=submission_date,
            opening_date=opening_date,
            pdf_url=pdf_link,
        )

    def _extract_value(self, texts: List[str]) -> Optional[float]:
        """Extract tender value from cell texts."""
        for text in texts:
            # Match patterns like "Rs. 5,00,000" or "₹ 50 Lakh" or "5.00 Cr"
            match = re.search(r'[\d,]+\.?\d*\s*(?:lakh|lac|cr|crore)', text.lower())
            if match:
                num_str = re.search(r'[\d,]+\.?\d*', match.group())
                if num_str:
                    value = float(num_str.group().replace(",", ""))
                    if "cr" in match.group().lower():
                        return value * 100  # Convert Cr to Lakh
                    return value

            # Match plain numbers that look like values
            match = re.search(r'(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)', text)
            if match:
                value = float(match.group().replace(",", ""))
                if value > 10000:  # Likely in Rs., convert to Lakh
                    return value / 100000
        return None
