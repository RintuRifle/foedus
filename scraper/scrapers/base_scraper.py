"""
Foedus — Abstract Base Scraper
All portal-specific scrapers inherit from this class.
Provides retry logic, rate limiting, and consistent output format.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

import httpx
from loguru import logger

@dataclass
class ScrapedTender:
    """Standardized tender data from any portal."""
    external_id: str
    source: str
    title: str
    description: Optional[str] = None
    sector: Optional[List[str]] = None
    state: Optional[str] = None
    department: Optional[str] = None
    organization: Optional[str] = None
    value_lakh: Optional[float] = None
    emd_amount: Optional[float] = None
    tender_fee: Optional[float] = None
    submission_date: Optional[date] = None
    opening_date: Optional[date] = None
    published_date: Optional[date] = None
    pdf_url: Optional[str] = None
    extra_data: Dict = field(default_factory=dict)

class BaseScraper(ABC):
    """
    Abstract base class for all tender portal scrapers.

    Features:
    - Rotating user agents to avoid blocking
    - Configurable retry with exponential backoff
    - Rate limiting between requests
    - Consistent ScrapedTender output format
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        source_name: str,
        base_url: str,
        max_pages: int = 5,
        request_delay: float = 2.0,
        max_retries: int = 3,
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.max_pages = max_pages
        self.request_delay = request_delay
        self.max_retries = max_retries

    def _get_headers(self) -> Dict[str, str]:
        """Random user-agent headers."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def _fetch_page(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """Fetch a page with retry and backoff."""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True,
                    verify=False,
                ) as client:
                    response = await client.get(
                        url,
                        headers=self._get_headers(),
                        params=params,
                    )
                    response.raise_for_status()
                    return response.text

            except httpx.HTTPStatusError as e:
                logger.warning(f"   HTTP {e.response.status_code} for {url} (attempt {attempt + 1})")
                if e.response.status_code == 429:
                    wait = (2 ** attempt) * 5  # Longer wait for rate limit
                    logger.info(f"   Rate limited — waiting {wait}s")
                    await asyncio.sleep(wait)
                elif e.response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"   Connection error for {url}: {e} (attempt {attempt + 1})")
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"   Unexpected error fetching {url}: {e}")
                return None

        logger.error(f"   ❌ Failed to fetch {url} after {self.max_retries} attempts")
        return None

    async def _rate_limit_delay(self):
        """Add random delay between requests to avoid detection."""
        delay = self.request_delay + random.uniform(0.5, 2.0)
        await asyncio.sleep(delay)

    @abstractmethod
    async def fetch_tenders(self) -> List[ScrapedTender]:
        """
        Scrape tender listings from the portal.
        Must be implemented by each portal-specific scraper.
        Returns list of ScrapedTender objects.
        """
        raise NotImplementedError

    async def run(self) -> List[ScrapedTender]:
        """Execute the scraper with logging."""
        logger.info(f"🔍 Starting scraper: {self.source_name}")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   Max pages: {self.max_pages}")

        try:
            tenders = await self.fetch_tenders()
            logger.info(f"   ✅ {self.source_name}: scraped {len(tenders)} tenders")
            return tenders
        except Exception as e:
            logger.error(f"   ❌ {self.source_name} scraper failed: {e}")
            return []
