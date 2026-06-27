"""FastAPI application for AFCS."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from afcs_api.db import Base, engine
from afcs_api.middleware.rate_limit import limiter
from afcs_api.routes import (
    actions,
    agent,
    artifacts,
    evaluations,
    events,
    expert_review,
    replay,
    reports,
    sessions,
    stakeholders,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Adaptive FDE Case Simulator API",
        description="Simulation sessions, actions, artifacts, and evaluation for FDE cases.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add a request ID header to every response."""
        import uuid

        request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------

    app.include_router(sessions.router)
    app.include_router(agent.router)
    app.include_router(actions.router)
    app.include_router(events.router)
    app.include_router(artifacts.router)
    app.include_router(reports.router)
    app.include_router(stakeholders.router)
    app.include_router(evaluations.router)
    app.include_router(replay.router)
    app.include_router(expert_review.router)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "afcs-api"}

    # ------------------------------------------------------------------
    # Lifespan
    # ------------------------------------------------------------------

    @app.on_event("startup")
    def on_startup():
        """Create tables on startup (dev convenience)."""
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
