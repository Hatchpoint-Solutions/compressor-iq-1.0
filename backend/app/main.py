"""CompressorIQ — FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import configure_logging, settings
from app.core.database import Base, engine

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.VERSION)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # For development convenience, auto-create tables.
    # In production, use Alembic migrations instead.
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Compressor service intelligence — data ingestion and management layer",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that prevents raw tracebacks from leaking to clients."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error",
        },
    )


# Import all models so that Base.metadata knows about them
from app import models as _models  # noqa: F401, E402

from app.api.routes import (  # noqa: E402
    analytics,
    compressors,
    dashboard,
    feedback,
    imports,
    ingestion,
    managers,
    notifications,
    recommendations,
    service_events,
    technicians,
    work_orders,
)

app.include_router(imports.router)
app.include_router(service_events.router)
app.include_router(compressors.router)
app.include_router(dashboard.router)
app.include_router(recommendations.router)
app.include_router(feedback.router)
app.include_router(analytics.router)
app.include_router(ingestion.router)
app.include_router(technicians.router)
app.include_router(managers.router)
app.include_router(work_orders.router)
app.include_router(notifications.router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}
