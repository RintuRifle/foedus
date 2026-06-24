"""
Foedus — Agent Output Schemas
Pydantic models used as structured output targets for Gemini.
Each agent returns one of these schemas.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class PreprocessorOutput(BaseModel):
    """Agent 0: Document analysis results."""
    pdf_type: str = Field(description="text | scanned | hybrid | unknown")
    page_count: int = Field(default=0, description="Total pages in document")
    language: str = Field(default="english", description="Primary language detected")
    has_eligibility_section: bool = Field(default=False)
    has_scope_section: bool = Field(default=False)
    has_financial_section: bool = Field(default=False)
    has_timeline_section: bool = Field(default=False)
    key_sections: List[str] = Field(
        default_factory=list,
        description="Identified section headings from the document"
    )
    tender_summary: str = Field(
        default="",
        description="2-3 sentence summary of what this tender is about"
    )


class MatchResult(BaseModel):
    """Agent 1: Company-tender matching score and reasons."""
    overall_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall match confidence 0.0 to 1.0"
    )
    sector_match: float = Field(ge=0.0, le=1.0, default=0.0)
    budget_match: float = Field(ge=0.0, le=1.0, default=0.0)
    location_match: float = Field(ge=0.0, le=1.0, default=0.0)
    experience_match: float = Field(ge=0.0, le=1.0, default=0.0)
    certification_match: float = Field(ge=0.0, le=1.0, default=0.0)
    match_reasons: List[str] = Field(
        default_factory=list,
        description="Human-readable reasons why this tender matches"
    )
    mismatch_reasons: List[str] = Field(
        default_factory=list,
        description="Areas where the company doesn't fit"
    )
    recommendation: str = Field(
        default="evaluate",
        description="strong_match | good_match | moderate | weak_match | skip"
    )


class ComplianceItemSchema(BaseModel):
    """Single eligibility criterion from the tender."""
    criterion: str = Field(description="The requirement stated in the tender")
    category: str = Field(
        default="general",
        description="financial | technical | legal | experience | certification | general"
    )
    required_value: str = Field(default="", description="What the tender requires")
    company_value: str = Field(default="", description="What the company has")
    status: Literal["met", "partial", "missing"] = Field(
        description="Whether the company meets this criterion"
    )
    source_quote: str = Field(
        default="",
        description="Exact quote from tender document for this criterion"
    )
    notes: str = Field(default="", description="Additional context or action needed")


class AuditResult(BaseModel):
    """Agent 2: Full eligibility audit result."""
    overall_status: str = Field(
        description="eligible | partially_eligible | not_eligible"
    )
    met_count: int = Field(default=0)
    partial_count: int = Field(default=0)
    missing_count: int = Field(default=0)
    compliance_items: List[ComplianceItemSchema] = Field(default_factory=list)
    missing_documents: List[str] = Field(
        default_factory=list,
        description="Documents the company needs to upload/obtain"
    )
    critical_gaps: List[str] = Field(
        default_factory=list,
        description="Showstopper issues that prevent participation"
    )
    summary: str = Field(default="", description="Brief eligibility summary")


class RiskResult(BaseModel):
    """Agent 3: Risk assessment and win probability."""
    win_probability: float = Field(
        ge=0.0, le=1.0,
        description="Estimated probability of winning (0.0 to 1.0)"
    )
    competition_level: str = Field(
        default="medium",
        description="low | medium | high | very_high"
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Specific risks identified"
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Company advantages for this tender"
    )
    recommendation: str = Field(
        default="bid",
        description="bid | conditional_bid | skip"
    )
    bid_strategy: str = Field(
        default="",
        description="Strategic advice for this particular bid"
    )
    estimated_competition: int = Field(
        default=5,
        description="Estimated number of competing bidders"
    )


class ReviewResult(BaseModel):
    """Agent 5: Proposal review/critique."""
    approved: bool = Field(
        description="Whether the proposal is ready for submission"
    )
    overall_score: int = Field(
        ge=1, le=10,
        description="Quality score 1-10"
    )
    completeness_score: int = Field(ge=1, le=10, default=5)
    accuracy_score: int = Field(ge=1, le=10, default=5)
    professionalism_score: int = Field(ge=1, le=10, default=5)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    revision_notes: str = Field(
        default="",
        description="Specific changes needed if not approved"
    )
    final_verdict: str = Field(
        default="",
        description="One-line summary of the review"
    )
