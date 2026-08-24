"""FastAPI application entry point.

All cross-cutting concerns (CORS, logging, lifespan, global error handling)
are configured here. No business logic lives in this file.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.common.exceptions import NexusSQLError
from app.common.logging import configure_logging, get_logger
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level)
    logger = get_logger("app.main")
    logger.info(
        "NEXUS-SQL starting | env=%s use_oracle=%s embedding=%s",
        settings.app_env.value,
        settings.use_oracle,
        settings.embedding_provider.value,
    )

    # Warm up schema cache so first query isn't slow
    try:
        from app.schema.manager import get_schema_manager
        snap = get_schema_manager().get_snapshot()
        logger.info("Schema warmed: %d tables", len(snap.tables))
    except Exception as exc:
        logger.warning("Schema warm-up failed (non-fatal): %s", exc)

    yield

    # Shutdown: close pool if open
    if settings.use_oracle:
        try:
            from app.database.connection import get_pool
            get_pool().close()
        except Exception as exc:
            get_logger("app.main").warning("Pool close error: %s", exc)

    get_logger("app.main").info("NEXUS-SQL stopped.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="NEXUS-SQL: Adaptive Hybrid Research Paper Retrieval",
        description=(
            "Advanced SQL project: NL-to-SQL pipeline with hybrid vector/structured "
            "retrieval, Oracle 23ai vector support, incremental error recovery, "
            "and multi-turn conversation."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Domain error → HTTP ───────────────────────────────────────────────────
    @app.exception_handler(NexusSQLError)
    async def nexus_error_handler(request: Request, exc: NexusSQLError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": type(exc).__name__, "message": str(exc)},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api")

    # ── Frontend ──────────────────────────────────────────────────────────────
    import os
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    frontend_dir = Path(__file__).parent.parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/")
        async def serve_index():
            return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=(settings.app_env.value == "development"),
        log_level=settings.log_level.lower(),
    )
