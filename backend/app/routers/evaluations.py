"""
Foedus — Evaluations Router
Trigger, monitor, and read results of AI tender evaluations.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.evaluation import ComplianceItem, EvaluationJob
from app.models.tender import Tender
from app.models.user import User
from app.schemas.evaluation import (
    ComplianceItemResponse,
    EvalProgressResponse,
    EvalReportResponse,
)
from app.tasks.evaluation_task import evaluate_tender_task
from app.utils.billing import ensure_plan_current
from app.utils.logger import logger

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


class EvaluationStartRequest(BaseModel):
    tender_id: uuid.UUID


class EvaluationResponse(BaseModel):
    job_id: str
    tender_id: str
    status: str
    message: str


async def _get_owned_job(
    job_id: str, user: User, db: AsyncSession
) -> EvaluationJob:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    job = await db.get(EvaluationJob, job_uuid)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Evaluation job not found")
    return job


@router.post("/start", response_model=EvaluationResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_evaluation(
    req: EvaluationStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a background 6-agent LangGraph evaluation for a tender.
    Returns immediately (202) with a job_id — track progress via
    WebSocket /ws/evaluations/{job_id} or polling /{job_id}/status.
    """
    # ── Plan quota check (downgrades expired Pro first) ───────
    current_user = await ensure_plan_current(current_user, db)
    if not current_user.can_evaluate:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly evaluation limit reached ({current_user.eval_limit} on "
                f"'{current_user.plan}' plan). Upgrade to Pro for unlimited evaluations."
            ),
        )

    # ── Verify tender exists ──────────────────────────────────
    tender = await db.get(Tender, req.tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # ── Guard: no duplicate running job for same user+tender ──
    existing = (
        await db.execute(
            select(EvaluationJob).where(
                EvaluationJob.user_id == current_user.id,
                EvaluationJob.tender_id == tender.id,
                EvaluationJob.status.in_(["pending", "queued", "running"]),
            )
        )
    ).scalars().first()
    if existing:
        return EvaluationResponse(
            job_id=str(existing.id),
            tender_id=str(tender.id),
            status="already_running",
            message="An evaluation for this tender is already in progress",
        )

    # ── Create job record ─────────────────────────────────────
    job = EvaluationJob(
        tender_id=tender.id,
        user_id=current_user.id,
        status="queued",
        current_agent="init",
        progress_pct=0,
    )
    db.add(job)
    current_user.evals_used += 1
    await db.commit()
    await db.refresh(job)

    # ── Queue Celery task ─────────────────────────────────────
    try:
        task = evaluate_tender_task.delay(
            job_id=str(job.id),
            tender_id=str(tender.id),
            user_id=str(current_user.id),
        )
        job.celery_task_id = task.id
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to queue celery task: {e}")
        job.status = "failed"
        job.error_log = str(e)
        current_user.evals_used -= 1  # Refund the quota
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue evaluation task")

    return EvaluationResponse(
        job_id=str(job.id),
        tender_id=str(tender.id),
        status="accepted",
        message="Evaluation pipeline started in background",
    )


@router.get("", response_model=list[EvalProgressResponse])
async def list_evaluations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User's evaluation history (pipeline view), newest first."""
    jobs = (
        await db.execute(
            select(EvaluationJob)
            .where(EvaluationJob.user_id == current_user.id)
            .order_by(desc(EvaluationJob.created_at))
            .limit(50)
        )
    ).scalars().all()
    return [
        EvalProgressResponse(
            job_id=j.id,
            status=j.status,
            progress_pct=j.progress_pct,
            current_agent=j.current_agent,
            current_message=j.current_message,
            started_at=j.started_at,
            duration_seconds=j.duration_seconds,
        )
        for j in jobs
    ]


@router.get("/{job_id}/status", response_model=EvalProgressResponse)
async def get_evaluation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Polling fallback for progress (use the WebSocket for live updates).
    """
    job = await _get_owned_job(job_id, current_user, db)
    return EvalProgressResponse(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        current_agent=job.current_agent,
        current_message=job.current_message,
        started_at=job.started_at,
        duration_seconds=job.duration_seconds,
    )


@router.get("/{job_id}/report", response_model=EvalReportResponse)
async def get_evaluation_report(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full structured report for a completed evaluation:
    match score + compliance matrix (green/red) + risk analysis.
    """
    job = await _get_owned_job(job_id, current_user, db)

    if job.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Evaluation still {job.status}. Report available once completed.",
        )
    if job.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evaluation failed — no report available. Re-run the evaluation.",
        )

    tender = await db.get(Tender, job.tender_id)
    items = (
        await db.execute(
            select(ComplianceItem)
            .where(ComplianceItem.evaluation_id == job.id)
            .order_by(ComplianceItem.sort_order)
        )
    ).scalars().all()

    match = job.match_result or {}
    audit = job.audit_result or {}
    risk = job.risk_result or {}

    return EvalReportResponse(
        job_id=job.id,
        tender_title=tender.title if tender else "Unknown tender",
        status=job.status,
        match_score=match.get("overall_score"),
        match_reasons=match.get("match_reasons"),
        eligibility_status=audit.get("overall_status"),
        compliance_matrix=[
            ComplianceItemResponse.model_validate(i) for i in items
        ],
        win_probability=risk.get("win_probability"),
        risk_factors=risk.get("risk_factors"),
        competition_level=risk.get("competition_level"),
        duration_seconds=job.duration_seconds,
        completed_at=job.completed_at,
    )
