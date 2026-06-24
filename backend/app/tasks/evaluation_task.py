"""
Foedus — Evaluation Celery Task
Runs the 6-agent pipeline asynchronously in the background.
"""

import asyncio
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.agents.graph import run_evaluation
from app.database import async_session_factory
from app.models.evaluation import ComplianceItem, EvaluationJob
from app.models.proposal import Proposal
from app.tasks import celery_app
from app.utils.logger import logger


@celery_app.task(
    name="foedus.evaluate_tender",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
)
def evaluate_tender_task(self, job_id: str, tender_id: str, user_id: str):
    """
    Celery task that runs the full evaluation pipeline.

    Flow:
    1. Update EvaluationJob status → running
    2. Run 6-agent LangGraph pipeline
    3. Save results to EvaluationJob (match, audit, risk)
    4. Save ComplianceItems from audit
    5. Save Proposal from writer
    6. Update status → completed / failed
    """
    logger.info(f"📋 Celery task starting: job={job_id}")

    # Run the async pipeline in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _run_evaluation_async(self, job_id, tender_id, user_id)
        )
    except Exception as e:
        logger.error(f"Celery task failed: {e}")
        loop.run_until_complete(_mark_failed(job_id, str(e)))
    finally:
        loop.close()


async def _run_evaluation_async(task, job_id: str, tender_id: str, user_id: str):
    """Async wrapper for the evaluation pipeline."""

    async with async_session_factory() as db:
        # Step 1: Mark job as running
        job = await db.get(EvaluationJob, uuid.UUID(job_id))
        if not job:
            raise ValueError(f"EvaluationJob {job_id} not found")

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.current_agent = "context_builder"
        job.celery_task_id = task.request.id
        await db.commit()

        try:
            # Step 2: Run the pipeline
            final_state = await run_evaluation(
                tender_id=tender_id,
                user_id=user_id,
                db_session=db,
                job_id=job_id,
            )

            # Step 3: Save results to EvaluationJob
            job.match_result = final_state.get("match_result")
            job.audit_result = final_state.get("audit_result")
            job.risk_result = final_state.get("risk_result")
            job.final_result = {
                "preprocessor": final_state.get("preprocessor_result"),
                "review": final_state.get("review_result"),
                "revision_count": final_state.get("revision_count", 0),
            }
            job.current_agent = "completed"
            job.progress_pct = 100
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)

            # Step 4: Save ComplianceItems
            audit = final_state.get("audit_result", {})
            for i, item in enumerate(audit.get("compliance_items", [])):
                compliance = ComplianceItem(
                    evaluation_id=job.id,
                    criterion=item.get("criterion", ""),
                    category=item.get("category", "general"),
                    required_value=item.get("required_value", ""),
                    user_value=item.get("company_value", ""),
                    status=item.get("status", "missing"),
                    source_quote=item.get("source_quote", ""),
                    notes=item.get("notes", ""),
                    sort_order=i,
                )
                db.add(compliance)

            # Step 5: Save Proposal
            final_proposal = final_state.get("final_proposal") or final_state.get("proposal_draft", "")
            if final_proposal:
                proposal = Proposal(
                    user_id=uuid.UUID(user_id),
                    tender_id=uuid.UUID(tender_id),
                    evaluation_id=job.id,
                    title=f"Proposal: {final_state.get('tender_title', 'Tender')[:100]}",
                    content_md=final_proposal,
                    version=1,
                    status="draft",
                )
                db.add(proposal)

            await db.commit()
            logger.info(f"✅ Evaluation job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")
            job.status = "failed"
            job.error_log = f"{str(e)}\n{traceback.format_exc()}"
            job.current_agent = "error"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise


async def _mark_failed(job_id: str, error: str):
    """Mark job as failed in DB (called from outer exception handler)."""
    try:
        async with async_session_factory() as db:
            job = await db.get(EvaluationJob, uuid.UUID(job_id))
            if job:
                job.status = "failed"
                job.error_log = error
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as e:
        logger.error(f"Failed to mark job as failed: {e}")
