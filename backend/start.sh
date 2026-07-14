#!/bin/bash
# Foedus — single-process startup (512MB free-tier safe)
#
# Everything runs inside ONE uvicorn process:
#   · API + WebSockets  → uvicorn
#   · Evaluations       → TASK_RUNNER=inline (asyncio tasks)
#   · Embeddings        → EMBEDDING_PROVIDER=gemini (API, no torch)
#   · Scraper           → POST /api/v1/scraper/trigger
#                         (GitHub Actions cron hits it daily at 6AM IST)
#
# The old multi-process version (celery + scheduler daemon + uvicorn)
# needed 3x the RAM and OOM'd the free tier. Never again.

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
