"""
Foedus — Helper Utilities
Common functions used across the codebase.
"""

import hashlib
import re
from datetime import date, datetime, timezone
from typing import List, Optional

def generate_content_hash(title: str, department: str = "", submission_date: str = "") -> str:
    """
    Generate SHA-256 hash for tender deduplication.
    Uses title + department + submission_date as composite key.
    """
    content = f"{title.strip().lower()}|{department.strip().lower()}|{submission_date}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def clean_text(text: str) -> str:
    """Remove extra whitespace, control characters, and normalize text."""
    if not text:
        return ""
    # Remove control characters except newlines
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Normalize newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    Uses word boundaries to avoid splitting mid-word.
    """
    if not text:
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break

    return chunks

def format_inr(amount_lakh: Optional[float]) -> str:
    """Format amount in Lakhs to readable Indian currency string."""
    if amount_lakh is None:
        return "N/A"
    if amount_lakh >= 100:
        return f"₹{amount_lakh / 100:.2f} Cr"
    return f"₹{amount_lakh:.2f} Lakh"

def parse_date_flexible(date_str: str) -> Optional[date]:
    """Parse dates in common Indian government formats."""
    if not date_str:
        return None

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d.%m.%Y",
        "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis at word boundary."""
    if not text or len(text) <= max_length:
        return text or ""
    truncated = text[:max_length].rsplit(" ", 1)[0]
    return truncated + "..."

def now_utc() -> datetime:
    """Current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)
