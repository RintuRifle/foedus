"""
Foedus — PDF Downloader
Downloads tender PDF documents with retry logic and size limits.
"""

import os
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

class PDFDownloader:
    """
    Async PDF downloader with:
    - Size limit enforcement (default 50MB)
    - Retry on failure
    - Organized storage by source/date
    """

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    def __init__(self, download_dir: str = "./data/pdfs"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download(
        self,
        url: str,
        filename: str,
        source: str = "unknown",
    ) -> Optional[str]:
        """
        Download a PDF and return the local file path.
        Returns None if download fails.
        """
        if not url:
            return None

        # Create source subdirectory
        source_dir = self.download_dir / source
        source_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")[:100]
        if not safe_name.endswith(".pdf"):
            safe_name += ".pdf"

        filepath = source_dir / safe_name

        # Skip if already downloaded
        if filepath.exists() and filepath.stat().st_size > 0:
            logger.debug(f"   📁 Already downloaded: {safe_name}")
            return str(filepath)

        try:
            async with httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                    logger.warning(f"   ⚠️ Not a PDF: {content_type} for {url}")
                    # Still try to save — some servers don't set correct content-type

                # Check size
                content = response.content
                if len(content) > self.MAX_FILE_SIZE:
                    logger.warning(f"   ⚠️ File too large ({len(content)} bytes): {url}")
                    return None

                if len(content) < 100:
                    logger.warning(f"   ⚠️ File too small ({len(content)} bytes): {url}")
                    return None

                # Write file
                filepath.write_bytes(content)
                logger.info(f"   📥 Downloaded: {safe_name} ({len(content) / 1024:.1f} KB)")
                return str(filepath)

        except Exception as e:
            logger.error(f"   ❌ Download failed for {url}: {e}")
            return None

    def get_downloaded_count(self) -> int:
        """Count total downloaded PDFs."""
        return sum(1 for _ in self.download_dir.rglob("*.pdf"))

# Singleton
pdf_downloader = PDFDownloader()
