"""
Foedus — Proposals Router
List, view, edit, and export AI-generated proposals.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.proposal import Proposal
from app.models.user import User
from app.schemas.proposal import ProposalResponse, ProposalUpdate
from app.utils.logger import logger

router = APIRouter(prefix="/proposals", tags=["Proposals"])


async def _get_owned_proposal(
    proposal_id: uuid.UUID, user: User, db: AsyncSession
) -> Proposal:
    proposal = await db.get(Proposal, proposal_id)
    if proposal is None or proposal.user_id != user.id:
        # 404 (not 403) so we don't leak existence of other users' proposals
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.get("", response_model=list[ProposalResponse])
async def list_proposals(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All proposals belonging to the authenticated user."""
    query = select(Proposal).where(Proposal.user_id == current_user.id)
    if status_filter:
        query = query.where(Proposal.status == status_filter)
    proposals = (
        await db.execute(
            query.order_by(desc(Proposal.updated_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()
    return proposals


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_owned_proposal(proposal_id, current_user, db)


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: uuid.UUID,
    body: ProposalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Edit a proposal (title / markdown content / status).
    Every content edit bumps the version number.
    """
    proposal = await _get_owned_proposal(proposal_id, current_user, db)

    if body.title is not None:
        proposal.title = body.title
    if body.content_md is not None and body.content_md != proposal.content_md:
        proposal.content_md = body.content_md
        proposal.version += 1
    if body.status is not None:
        allowed = {"draft", "reviewed", "submitted", "archived"}
        if body.status not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status. Allowed: {sorted(allowed)}",
            )
        proposal.status = body.status

    await db.commit()
    await db.refresh(proposal)
    return proposal


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    proposal = await _get_owned_proposal(proposal_id, current_user, db)
    await db.delete(proposal)
    await db.commit()


@router.get("/{proposal_id}/export.md")
async def export_markdown(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the proposal as a Markdown file."""
    proposal = await _get_owned_proposal(proposal_id, current_user, db)
    filename = (proposal.title or "proposal").replace('"', "")[:80]
    return Response(
        content=proposal.content_md or "",
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.md"'},
    )


@router.get("/{proposal_id}/export.pdf")
async def export_pdf(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the proposal as a styled PDF (Markdown → HTML → WeasyPrint).
    """
    proposal = await _get_owned_proposal(proposal_id, current_user, db)

    try:
        import markdown as md_lib
        from weasyprint import HTML
    except (ImportError, OSError) as e:
        # WeasyPrint needs system libs (pango/cairo); degrade gracefully
        logger.error(f"PDF export unavailable: {e}")
        raise HTTPException(
            status_code=501,
            detail="PDF export not available on this server. Use /export.md instead.",
        )

    body_html = md_lib.markdown(
        proposal.content_md or "", extensions=["tables", "fenced_code"]
    )
    html = f"""<!DOCTYPE html>
    <html><head><meta charset="utf-8"><style>
        @page {{ size: A4; margin: 2.2cm 1.8cm; }}
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt;
               color: #1a1a2e; line-height: 1.55; }}
        h1 {{ font-size: 19pt; border-bottom: 2px solid #16213e; padding-bottom: 6px; }}
        h2 {{ font-size: 14pt; color: #16213e; margin-top: 22px; }}
        h3 {{ font-size: 12pt; color: #0f3460; }}
        table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 6px 9px; font-size: 10pt; }}
        th {{ background: #f1f5f9; text-align: left; }}
        .footer {{ font-size: 8pt; color: #94a3b8; margin-top: 30px; }}
    </style></head>
    <body>{body_html}
    <p class="footer">Generated by Foedus AI — review before submission.</p>
    </body></html>"""

    pdf_bytes = HTML(string=html).write_pdf()
    filename = (proposal.title or "proposal").replace('"', "")[:80]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )
