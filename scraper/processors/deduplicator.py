"""
Foedus — Tender Deduplicator
Prevents the same tender from being stored multiple times.
Uses SHA-256 hash of (title + department + submission_date).
"""

from typing import Set

from loguru import logger
from sqlalchemy import select, text

from app.utils.helpers import generate_content_hash

class Deduplicator:
    """
    Hash-based deduplication for scraped tenders.

    Flow:
    1. Before processing, load all existing content hashes from DB
    2. For each scraped tender, compute hash
    3. Skip if hash already exists
    """

    def __init__(self):
        self._known_hashes: Set[str] = set()

    async def load_existing_hashes(self, db_session) -> int:
        """Load all existing tender content hashes from database."""
        from app.models.tender import Tender

        result = await db_session.execute(
            select(Tender.content_hash).where(Tender.content_hash.isnot(None))
        )
        self._known_hashes = {row[0] for row in result.fetchall()}
        logger.info(f"   📋 Loaded {len(self._known_hashes)} existing tender hashes")
        return len(self._known_hashes)

    def is_duplicate(self, title: str, department: str = "", submission_date: str = "") -> bool:
        """Check if a tender with this content already exists."""
        content_hash = generate_content_hash(title, department, submission_date)
        return content_hash in self._known_hashes

    def compute_hash(self, title: str, department: str = "", submission_date: str = "") -> str:
        """Compute the content hash for a tender."""
        return generate_content_hash(title, department, submission_date)

    def mark_seen(self, content_hash: str):
        """Add a hash to the known set (after successful insert)."""
        self._known_hashes.add(content_hash)

    @property
    def known_count(self) -> int:
        return len(self._known_hashes)

# Singleton
deduplicator = Deduplicator()
