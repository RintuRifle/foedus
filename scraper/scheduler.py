"""
Foedus — Scraper Scheduler
Orchestrates the complete tender ingestion pipeline:
  Scrape → Deduplicate → Classify → Download PDF → OCR → Embed → Store

Can run as:
  - One-shot: python -m scraper.scheduler --once
  - Daemon:   python -m scraper.scheduler (runs daily at 6 AM IST)
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from loguru import logger

from app.config import settings
from app.database import async_session_factory
from app.models.tender import Tender
from app.services.embedding_service import embedding_service
from app.services.ocr_service import ocr_service
from app.services.vectorstore_service import vectorstore_service
from scraper.processors.classifier import classifier
from scraper.processors.deduplicator import deduplicator
from scraper.processors.pdf_downloader import pdf_downloader
from scraper.scrapers.base_scraper import ScrapedTender
from scraper.scrapers.eprocure_scraper import EProcureScraper
from scraper.scrapers.gem_scraper import GeMScraper

async def run_pipeline():
    """
    Execute the full ingestion pipeline:
    1. Scrape tenders from all portals
    2. Deduplicate against existing DB
    3. Classify by sector (AI)
    4. Download PDFs
    5. Extract text (OCR)
    6. Generate embeddings
    7. Store in PostgreSQL + Qdrant
    """
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("🚀 Foedus Ingestion Pipeline Starting")
    logger.info(f"   Time: {start_time.isoformat()}")
    logger.info("=" * 60)

    stats = {
        "scraped": 0,
        "duplicates": 0,
        "new": 0,
        "classified": 0,
        "pdfs_downloaded": 0,
        "ocr_extracted": 0,
        "embedded": 0,
        "errors": 0,
    }

    # ── Step 1: Scrape from all portals ───────────────────────
    logger.info("\n📡 STEP 1: Scraping tender portals...")
    scrapers = [
        EProcureScraper(max_pages=settings.SCRAPER_MAX_PAGES),
        GeMScraper(max_pages=settings.SCRAPER_MAX_PAGES),
    ]

    all_tenders: list[ScrapedTender] = []
    for scraper in scrapers:
        tenders = await scraper.run()
        all_tenders.extend(tenders)

    stats["scraped"] = len(all_tenders)
    logger.info(f"   Total scraped: {stats['scraped']} tenders")

    if not all_tenders:
        logger.warning("   No tenders scraped — check portal connectivity")
        return stats

    # ── Step 2: Deduplicate ───────────────────────────────────
    logger.info("\n🔍 STEP 2: Deduplicating...")
    async with async_session_factory() as db:
        await deduplicator.load_existing_hashes(db)

    new_tenders = []
    for tender in all_tenders:
        dept = tender.department or tender.organization or ""
        sub_date = str(tender.submission_date) if tender.submission_date else ""

        if deduplicator.is_duplicate(tender.title, dept, sub_date):
            stats["duplicates"] += 1
            continue
        new_tenders.append(tender)

    stats["new"] = len(new_tenders)
    logger.info(f"   New tenders: {stats['new']} (skipped {stats['duplicates']} duplicates)")

    if not new_tenders:
        logger.info("   No new tenders to process")
        return stats

    # ── Step 3-7: Process each new tender ─────────────────────
    logger.info(f"\n⚙️  STEPS 3-7: Processing {len(new_tenders)} new tenders...")

    for i, tender in enumerate(new_tenders, 1):
        logger.info(f"\n{'─' * 40}")
        logger.info(f"   [{i}/{len(new_tenders)}] {tender.title[:60]}...")

        try:
            await process_single_tender(tender, stats)
        except Exception as e:
            logger.error(f"   ❌ Error processing tender: {e}")
            stats["errors"] += 1
            continue

    # ── Summary ───────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info("📊 Pipeline Complete!")
    logger.info(f"   Duration: {elapsed:.1f}s")
    logger.info(f"   Scraped: {stats['scraped']}")
    logger.info(f"   Duplicates: {stats['duplicates']}")
    logger.info(f"   New: {stats['new']}")
    logger.info(f"   Classified: {stats['classified']}")
    logger.info(f"   PDFs Downloaded: {stats['pdfs_downloaded']}")
    logger.info(f"   OCR Extracted: {stats['ocr_extracted']}")
    logger.info(f"   Embedded: {stats['embedded']}")
    logger.info(f"   Errors: {stats['errors']}")
    logger.info("=" * 60)

    return stats

async def process_single_tender(tender: ScrapedTender, stats: dict):
    """Process a single scraped tender through the full pipeline."""
    from app.utils.helpers import generate_content_hash

    # Step 3: Classify sector
    sectors = await classifier.classify(tender.title, tender.description or "")
    tender.sector = sectors
    stats["classified"] += 1
    logger.info(f"   🏷️  Sectors: {sectors}")

    # Step 4: Download PDF (if URL available)
    local_pdf = None
    if tender.pdf_url:
        local_pdf = await pdf_downloader.download(
            url=tender.pdf_url,
            filename=f"{tender.external_id}",
            source=tender.source,
        )
        if local_pdf:
            stats["pdfs_downloaded"] += 1

    # Step 5: Extract text (OCR)
    parsed_text = ""
    if local_pdf:
        parsed_text = await ocr_service.extract_text(local_pdf)
        if parsed_text:
            stats["ocr_extracted"] += 1
    elif tender.description:
        parsed_text = tender.description

    # Step 6: Generate embeddings & store in Qdrant
    tender_id_str = tender.external_id
    if parsed_text and len(parsed_text) > 50:
        chunks = embedding_service.embed_document(parsed_text)
        if chunks:
            vectorstore_service.upsert_chunks(
                tender_id=tender_id_str,
                chunks=chunks,
                source=tender.source,
                metadata={
                    "title": tender.title[:200],
                    "sector": tender.sector or [],
                },
            )
            stats["embedded"] += 1

    # Step 7: Store in PostgreSQL
    dept = tender.department or tender.organization or ""
    sub_date = str(tender.submission_date) if tender.submission_date else ""
    content_hash = generate_content_hash(tender.title, dept, sub_date)

    async with async_session_factory() as db:
        db_tender = Tender(
            external_id=tender.external_id,
            source=tender.source,
            title=tender.title,
            description=tender.description,
            sector=tender.sector,
            state=tender.state,
            department=tender.department,
            organization=tender.organization,
            value_lakh=tender.value_lakh,
            emd_amount=tender.emd_amount,
            tender_fee=tender.tender_fee,
            submission_date=tender.submission_date,
            opening_date=tender.opening_date,
            published_date=tender.published_date,
            pdf_url=tender.pdf_url,
            local_pdf_path=local_pdf,
            parsed_text=parsed_text if parsed_text else None,
            content_hash=content_hash,
            status="active",
        )
        db.add(db_tender)
        await db.commit()

    deduplicator.mark_seen(content_hash)
    logger.info(f"   ✅ Stored in DB + Vector DB")

def run_scheduler():
    """Run as a daemon with APScheduler (daily at 6 AM IST)."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(
            hour=settings.SCRAPER_CRON_HOUR,
            minute=settings.SCRAPER_CRON_MINUTE,
            timezone="Asia/Kolkata",
        ),
        id="daily_scrape",
        name="Daily Tender Scraping Pipeline",
    )

    logger.info(f"⏰ Scheduler started — next run at {settings.SCRAPER_CRON_HOUR}:{settings.SCRAPER_CRON_MINUTE:02d} IST")
    scheduler.start()

    # Keep the process alive
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
        scheduler.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Foedus Scraper Pipeline")
    parser.add_argument("--once", action="store_true", help="Run pipeline once and exit")
    args = parser.parse_args()

    if args.once:
        asyncio.run(run_pipeline())
    else:
        run_scheduler()
