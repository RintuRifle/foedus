"""
Foedus — Task Runner Dispatch
One switch, two execution models, same features:

  TASK_RUNNER=celery  — evaluations run in a separate Celery worker
                        (multi-instance scale, needs a paid worker dyno)
  TASK_RUNNER=inline  — evaluations run as asyncio tasks INSIDE the API
                        process. The pipeline is pure awaited I/O (LLM +
                        DB calls), so this costs ~zero extra RAM — which
                        is how everything fits on a 512MB free tier.

WebSocket progress, job tracking, and the 202-Accepted flow are identical
in both modes (both go through execute_evaluation → Redis pub/sub).
"""

import asyncio
from typing import Optional

from app.config import settings
from app.utils.logger import logger

# Keep strong references so in-flight inline tasks aren't garbage-collected
_inflight: set[asyncio.Task] = set()


def dispatch_evaluation(job_id: str, tender_id: str, user_id: str) -> Optional[str]:
    """
    Fire an evaluation in the configured runner.
    Returns the Celery task id (celery mode) or None (inline mode).
    Raises on dispatch failure so the caller can refund quota.
    """
    if settings.TASK_RUNNER.lower() == "celery":
        from app.tasks.evaluation_task import evaluate_tender_task
        task = evaluate_tender_task.delay(
            job_id=job_id, tender_id=tender_id, user_id=user_id
        )
        logger.info(f"📋 Dispatched to Celery: job={job_id} task={task.id}")
        return task.id

    # ── Inline: asyncio task in this process ──────────────────
    from app.tasks.evaluation_task import _mark_failed, execute_evaluation

    async def _guarded():
        try:
            await execute_evaluation(job_id, tender_id, user_id)
        except Exception as e:  # execute_evaluation logs details itself
            logger.error(f"Inline evaluation failed: job={job_id}: {e}")
            try:
                await _mark_failed(job_id, str(e))
            except Exception:
                pass

    task = asyncio.get_running_loop().create_task(_guarded())
    _inflight.add(task)
    task.add_done_callback(_inflight.discard)
    logger.info(f"📋 Dispatched inline: job={job_id} (in-flight: {len(_inflight)})")
    return None
