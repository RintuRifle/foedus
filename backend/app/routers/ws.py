"""
Foedus — WebSocket Router
Live evaluation progress streamed from Redis pub/sub.

Frontend usage:
    const ws = new WebSocket(
        `ws://localhost:8000/api/v1/ws/evaluations/${jobId}?token=${accessToken}`
    );
    ws.onmessage = (e) => {
        const ev = JSON.parse(e.data);
        // { job_id, agent, progress, message, status, timestamp }
    };
"""

import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.database import async_session_factory
from app.models.evaluation import EvaluationJob
from app.services.progress_service import subscribe_progress
from app.utils.logger import logger
from app.utils.security import decode_access_token

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# WebSocket close codes
WS_UNAUTHORIZED = 4001
WS_NOT_FOUND = 4004


@router.websocket("/evaluations/{job_id}")
async def evaluation_progress_ws(
    websocket: WebSocket,
    job_id: str,
    token: str = Query(default=None, description="JWT access token"),
):
    """
    Stream live agent-by-agent progress for an evaluation job.
    Closes automatically once the job completes or fails.

    Auth: browsers can't set headers on WebSockets, so the JWT is
    passed as a `?token=` query param.
    """
    await websocket.accept()

    # ── Validate job id ───────────────────────────────────────
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        await websocket.close(code=WS_NOT_FOUND, reason="Invalid job ID")
        return

    # ── Authenticate & authorize ──────────────────────────────
    payload = decode_access_token(token) if token else None
    if payload is None or payload.get("sub") is None:
        await websocket.close(code=WS_UNAUTHORIZED, reason="Invalid or missing token")
        return

    async with async_session_factory() as db:
        job = await db.get(EvaluationJob, job_uuid)
        if job is None:
            await websocket.close(code=WS_NOT_FOUND, reason="Job not found")
            return
        if str(job.user_id) != payload["sub"]:
            await websocket.close(code=WS_UNAUTHORIZED, reason="Not your job")
            return

        # If job already finished, send final state once and close
        if job.status in ("completed", "failed"):
            await websocket.send_json({
                "job_id": job_id,
                "agent": job.current_agent,
                "progress": job.progress_pct,
                "message": job.current_message or f"Job {job.status}",
                "status": job.status,
                "timestamp": (job.completed_at or job.created_at).isoformat(),
            })
            await websocket.close()
            return

    # ── Stream events from Redis until terminal event ─────────
    try:
        async for event in subscribe_progress(job_id):
            await websocket.send_json(event)
        await websocket.close()
    except WebSocketDisconnect:
        logger.debug(f"WS client disconnected: job {job_id}")
    except Exception as e:
        logger.warning(f"WS stream error for job {job_id}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
