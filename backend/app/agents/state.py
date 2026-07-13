"""
Foedus — Agent Pipeline State
TypedDict shared across all 6 LangGraph agents.
Each agent reads what it needs and writes its output.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state passed through the LangGraph pipeline.

    Flow:
    context_builder → Agent 0 → 1 → 2 → 3 → 4 → 5 → final

    'total=False' makes all keys optional so agents can
    incrementally populate the state.
    """

    # Input context (populated by context_builder before graph starts)
    tender_id: str
    user_id: str
    tender_text: str
    tender_title: str
    tender_metadata: dict          # source, sector, value, dates, etc.
    company_profile: dict          # Company model fields as dict
    company_documents: list[str]   # Parsed text from uploaded docs
    rag_context: list[str]         # Relevant chunks from Qdrant

    # Agent 0: Preprocessor output
    preprocessor_result: dict

    # Agent 1: Matchmaker output
    match_result: dict

    # Agent 2: Auditor output
    audit_result: dict

    # Agent 3: Risk Assessor output
    risk_result: dict

    # Agent 4: Writer output
    proposal_draft: str

    proposal_lint_issues: list        # Guardrail lint flags from Writer

    # Agent 5: Reviewer output
    review_result: dict
    final_proposal: str            # Approved version after review

    # Control flow
    current_agent: str
    progress_pct: int
    revision_count: int            # Writer ↔ Reviewer loop counter (max 2)
    error: Optional[str]

    # Evaluation job tracking
    job_id: str
