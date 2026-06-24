"""
Foedus — Evaluations Router
Endpoints for triggering and monitoring AI tender evaluations.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.evaluation import EvaluationJob
from app.models.tender import Tender
from app.models.user import User
from app.tasks.evaluation_task import evaluate_tender_task
from app.utils.logger import logger

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


class EvaluationStartRequest(BaseModel):
    tender_id: str


class EvaluationResponse(BaseModel):
    job_id: str
    tender_id: str
    status: str
    message: str


@router.post("/start", response_model=EvaluationResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_evaluation(
    req: EvaluationStartRequest,
    db: AsyncSession = Depends(get_db),
    # TODO: Add auth dependency once implemented
    # current_user: User = Depends(get_current_user)
):
    """
    Trigger a background 6-agent LangGraph evaluation for a tender.
    Returns immediately with a job_id for polling progress.
    """
    # For MVP without auth context injected here, we assume user_id is the first user
    # In production, replace this with the actual authenticated user
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="No user found to run evaluation")

    # Verify tender exists
    tender = await db.get(Tender, req.tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Create EvaluationJob record
    job = EvaluationJob(
        tender_id=tender.id,
        user_id=user.id,
        status="pending",
        current_agent="init",
        progress_pct=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Trigger Celery background task
    try:
        task = evaluate_tender_task.delay(
            job_id=str(job.id),
            tender_id=str(tender.id),
            user_id=str(user.id)
        )
        job.celery_task_id = task.id
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to queue celery task: {e}")
        job.status = "failed"
        job.error_log = str(e)
        await db.commit()
        raise HTTPException(
            status_code=500, detail="Failed to queue evaluation task"
        )

    return EvaluationResponse(
        job_id=str(job.id),
        tender_id=str(tender.id),
        status="accepted",
        message="Evaluation pipeline started in background",
    )


@router.get("/{job_id}/status")
async def get_evaluation_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Poll the status of an ongoing evaluation job.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = await db.get(EvaluationJob, job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Evaluation job not found")

    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress_pct": job.progress_pct,
        "current_agent": job.current_agent,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_log": job.error_log if job.status == "failed" else None
    }
