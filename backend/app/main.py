"""
Foedus — FastAPI Application Entry Point
Central app instance with CORS, routers, and lifecycle events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, company, evaluations, payments, proposals, tenders, ws
from app.utils.logger import logger
from app.utils.tracing import configure_langsmith

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Runs on startup and shutdown.
    """
    # ── Startup ───────────────────────────────────────────────
    logger.info("🚀 Foedus Backend starting up...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Debug: {settings.APP_DEBUG}")

    configure_langsmith()

    # Initialize Sentry if DSN is provided
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.APP_ENV,
        )
        logger.info("   Sentry initialized ✓")

    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("🛑 Foedus Backend shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Tender Discovery & Proposal Agent for Indian SMEs",
    version="1.0.0",
    docs_url="/docs" if settings.APP_DEBUG else None,
    redoc_url="/redoc" if settings.APP_DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(company.router, prefix="/api/v1")
app.include_router(tenders.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(proposals.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }

@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Foedus API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
