"""
Foedus — Scraper Trigger Router
Replaces the always-on scheduler daemon for free-tier deployments:
an external free cron (GitHub Actions / cron-job.org) hits this endpoint
daily at 6 AM IST, and the ingestion pipeline runs inside the API process.

Security: requires the X-Scraper-Token header to match SCRAPER_TRIGGER_TOKEN.
Bonus: the cron ping also wakes a sleeping free-tier instance.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/scraper", tags=["Scraper"])

_state = {"running": False, "last_started": None, "last_finished": None, "last_error": None}


def _import_pipeline():
    """Import the scraper pipeline (repo-root package, lazy)."""
    try:
        from scraper.scheduler import run_pipeline  # Docker: /app/scraper
        return run_pipeline
    except ImportError:
        # Local dev: backend/ is cwd, scraper lives one level up
        root = Path(__file__).resolve().parents[3]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from scraper.scheduler import run_pipeline
        return run_pipeline


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape(
    x_scraper_token: str = Header(default="", alias="X-Scraper-Token"),
):
    """
    Kick off one ingestion run (scrape → dedup → classify → OCR → embed → store).
    Returns 202 immediately; the pipeline runs as a background asyncio task.
    """
    if not settings.SCRAPER_TRIGGER_TOKEN:
        raise HTTPException(status_code=503, detail="Scraper trigger not configured")
    if x_scraper_token != settings.SCRAPER_TRIGGER_TOKEN:
        logger.warning("🕷️ Scraper trigger: bad token")
        raise HTTPException(status_code=401, detail="Invalid scraper token")

    if _state["running"]:
        return {"status": "already_running", "started_at": _state["last_started"]}

    run_pipeline = _import_pipeline()

    async def _run():
        _state["running"] = True
        _state["last_started"] = datetime.now(timezone.utc).isoformat()
        _state["last_error"] = None
        try:
            await run_pipeline()
            logger.info("🕷️ Triggered scrape finished")
        except Exception as e:
            _state["last_error"] = str(e)
            logger.error(f"🕷️ Triggered scrape failed: {e}")
        finally:
            _state["running"] = False
            _state["last_finished"] = datetime.now(timezone.utc).isoformat()

    asyncio.get_running_loop().create_task(_run())
    return {"status": "started", "note": "Pipeline running in background"}


@router.get("/status")
async def scrape_status(
    x_scraper_token: str = Header(default="", alias="X-Scraper-Token"),
):
    """Last run info (same token required)."""
    if x_scraper_token != settings.SCRAPER_TRIGGER_TOKEN or not settings.SCRAPER_TRIGGER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid scraper token")
    return _state
