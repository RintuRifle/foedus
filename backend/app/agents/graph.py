"""
Foedus — LangGraph Pipeline Assembly
Wires all 6 agents into a StateGraph with conditional Writer↔Reviewer loop.
"""

from langgraph.graph import END, StateGraph

from app.agents.agent_0_preprocessor import preprocessor_node
from app.agents.agent_1_matchmaker import matchmaker_node
from app.agents.agent_2_auditor import auditor_node
from app.agents.agent_3_risk import risk_node
from app.agents.agent_4_writer import writer_node
from app.agents.agent_5_reviewer import reviewer_node
from app.agents.context_builder import build_context
from app.agents.state import AgentState
from app.utils.logger import logger


def _should_revise(state: AgentState) -> str:
    """
    Conditional edge after Reviewer:
    - If proposal approved or max revisions reached → END
    - If needs revision → back to Writer
    """
    review = state.get("review_result", {})
    revision_count = state.get("revision_count", 0)

    if review.get("approved", False):
        return "end"
    if revision_count >= 2:
        return "end"
    return "revise"


def build_evaluation_graph() -> StateGraph:
    """
    Build the 6-agent LangGraph pipeline.

    Flow:
        preprocessor → matchmaker → auditor → risk → writer → reviewer
                                                        ↑         |
                                                        └─────────┘
                                                       (if revision needed)
    """
    graph = StateGraph(AgentState)

    # Add all agent nodes
    graph.add_node("preprocessor", preprocessor_node)
    graph.add_node("matchmaker", matchmaker_node)
    graph.add_node("auditor", auditor_node)
    graph.add_node("risk_assessor", risk_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)

    # Sequential edges: 0 → 1 → 2 → 3 → 4 → 5
    graph.set_entry_point("preprocessor")
    graph.add_edge("preprocessor", "matchmaker")
    graph.add_edge("matchmaker", "auditor")
    graph.add_edge("auditor", "risk_assessor")
    graph.add_edge("risk_assessor", "writer")
    graph.add_edge("writer", "reviewer")

    # Conditional edge: Reviewer → END or → Writer (revision loop)
    graph.add_conditional_edges(
        "reviewer",
        _should_revise,
        {
            "end": END,
            "revise": "writer",
        },
    )

    return graph


# Compile the graph once at import time
evaluation_graph = build_evaluation_graph().compile()


async def run_evaluation(
    tender_id: str,
    user_id: str,
    db_session,
    job_id: str = None,
) -> AgentState:
    """
    Execute the full 6-agent evaluation pipeline.

    Args:
        tender_id: UUID of the tender to evaluate
        user_id: UUID of the user requesting evaluation
        db_session: Async SQLAlchemy session
        job_id: Optional evaluation job ID for tracking

    Returns:
        Final AgentState with all agent outputs
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting Foedus Evaluation Pipeline")
    logger.info(f"   Tender: {tender_id}")
    logger.info(f"   User: {user_id}")
    logger.info("=" * 60)

    # Build initial state with all context
    initial_state = await build_context(
        tender_id=tender_id,
        user_id=user_id,
        db=db_session,
        job_id=job_id,
    )

    # Run the LangGraph pipeline
    final_state = await evaluation_graph.ainvoke(initial_state)

    logger.info("=" * 60)
    logger.info("✅ Evaluation Pipeline Complete!")
    match = final_state.get("match_result", {})
    risk = final_state.get("risk_result", {})
    review = final_state.get("review_result", {})
    logger.info(f"   Match Score: {match.get('overall_score', 'N/A')}")
    logger.info(f"   Win Probability: {risk.get('win_probability', 'N/A')}")
    logger.info(f"   Proposal Score: {review.get('overall_score', 'N/A')}/10")
    logger.info(f"   Revisions: {final_state.get('revision_count', 0)}")
    logger.info(f"   LLM Usage: {llm_service.usage_stats}")
    logger.info("=" * 60)

    return final_state


# Import here to avoid circular import
from app.services.llm_service import llm_service
