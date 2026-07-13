"""
Foedus — LangSmith Tracing
Enables per-agent LLM call tracing when LANGCHAIN_TRACING_V2=true in .env.

LangChain/LangGraph pick tracing config up from environment variables,
so we just promote our settings into os.environ at process start —
both in the FastAPI app and in the Celery worker.

View traces at https://smith.langchain.com under the 'foedus' project:
every evaluation shows the full 6-agent chain with prompts, outputs,
latencies, and token counts — the place to catch hallucination patterns.
"""

import os

from app.config import settings
from app.utils.logger import logger


def configure_langsmith() -> bool:
    """
    Promote LangSmith settings to environment variables.
    Returns True if tracing was enabled.
    """
    if not settings.LANGCHAIN_TRACING_V2:
        return False
    if not settings.LANGCHAIN_API_KEY:
        logger.warning(
            "LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY missing — tracing disabled"
        )
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    os.environ.setdefault(
        "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"
    )
    logger.info(f"🔬 LangSmith tracing ON — project '{settings.LANGCHAIN_PROJECT}'")
    return True
