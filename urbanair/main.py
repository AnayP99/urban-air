from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from urbanair.config import get_settings
from urbanair.routers.summary import router as summary_router

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)
app.mount("/static", StaticFiles(directory="urbanair/static"), name="static")
app.include_router(summary_router)


@app.get("/healthz")
async def healthcheck():
    return JSONResponse({"ok": True, "app": settings.app_name})
