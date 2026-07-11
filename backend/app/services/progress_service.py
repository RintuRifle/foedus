"""
Foedus — Progress Service (Redis Pub/Sub)
Bridges the Celery worker and the FastAPI WebSocket endpoint.

Worker side:  publish_progress() → Redis channel `foedus:progress:{job_id}`
API side:     subscribe_progress() → async generator of events for WebSocket

The latest event is also cached (SETEX, 1h TTL) so a client that connects
mid-evaluation immediately receives the current state instead of silence.
"""

import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis

from app.config import settings
from app.utils.logger import logger

CHANNEL_PREFIX = "foedus:progress:"
SNAPSHOT_PREFIX = "foedus:progress:snapshot:"
SNAPSHOT_TTL_SECONDS = 3600

# Module-level async Redis client (lazy singleton)
_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


def _build_event(
    job_id: str, agent: str, progress: int, message: str, status: str
) -> dict:
    return {
        "job_id": job_id,
        "agent": agent,
        "progress": progress,
        "message": message,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def publish_progress(
    job_id: str,
    agent: str,
    progress: int,
    message: str,
    status: str = "running",
) -> None:
    """
    Publish a progress event. Called by the Celery worker after each
    agent node completes. Never raises — progress is best-effort and
    must not kill the evaluation pipeline.
    """
    event = _build_event(job_id, agent, progress, message, status)
    payload = json.dumps(event)
    try:
        r = get_redis()
        await r.publish(f"{CHANNEL_PREFIX}{job_id}", payload)
        await r.setex(f"{SNAPSHOT_PREFIX}{job_id}", SNAPSHOT_TTL_SECONDS, payload)
    except Exception as e:
        logger.warning(f"Progress publish failed for job {job_id}: {e}")


async def get_progress_snapshot(job_id: str) -> Optional[dict]:
    """Return the last published event for a job, if any."""
    try:
        raw = await get_redis().get(f"{SNAPSHOT_PREFIX}{job_id}")
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Progress snapshot read failed for job {job_id}: {e}")
        return None


async def subscribe_progress(job_id: str) -> AsyncGenerator[dict, None]:
    """
    Async generator yielding progress events for a job.
    Terminates automatically once a terminal event arrives.
    Used by the WebSocket endpoint.
    """
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"{CHANNEL_PREFIX}{job_id}")
    try:
        # Replay the latest snapshot first (late-joiner catch-up)
        snapshot = await get_progress_snapshot(job_id)
        if snapshot:
            yield snapshot
            if snapshot.get("status") in ("completed", "failed"):
                return

        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            try:
                event = json.loads(msg["data"])
            except (json.JSONDecodeError, TypeError):
                continue
            yield event
            if event.get("status") in ("completed", "failed"):
                return
    finally:
        await pubsub.unsubscribe(f"{CHANNEL_PREFIX}{job_id}")
        await pubsub.aclose()
