"""UrbanAir FastAPI application — entry point and lifespan configuration."""
from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from urbanair.cache.cache_manager import InMemoryTTLCache
from urbanair.config import get_settings
from urbanair.routers.api import router as api_router
from urbanair.routers.pages import router as pages_router
from urbanair.services.analytics_service import AnalyticsService
from urbanair.services.waitlist_service import WaitlistService
from urbanair.storage import Storage

from pathlib import Path

settings = get_settings()
_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATES_DIR = Path(__file__).parent / "templates"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize shared services on startup and clean up on shutdown."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    app.state.cache = InMemoryTTLCache(ttl_seconds=settings.cache_ttl_seconds)
    app.state.storage = Storage(settings.storage_path)
    app.state.analytics_service = AnalyticsService(app.state.storage)
    app.state.waitlist_service = WaitlistService(app.state.storage)
    yield
    logger.info("Shutting down %s", settings.app_name)
    app.state.cache.clear()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.include_router(pages_router)
app.include_router(api_router)


@app.get("/healthz")
async def healthcheck() -> dict:
    """Simple liveness check. Use /api/health for the structured response."""
    return {"ok": True, "app": settings.app_name}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> Response:
    if request.url.path.startswith("/api/"):
        detail = exc.detail if isinstance(exc, HTTPException) else "Not found"
        return JSONResponse(status_code=404, content={"detail": detail})

    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={
            "request": request,
            "app_name": settings.app_name,
            "page_title": f"Page not found | {settings.app_name}",
        },
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception) -> Response:
    logger.exception("Unhandled server error on %s: %s", request.url.path, exc)
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return templates.TemplateResponse(
        request=request,
        name="500.html",
        context={
            "request": request,
            "app_name": settings.app_name,
            "page_title": f"Something went wrong | {settings.app_name}",
        },
        status_code=500,
    )
