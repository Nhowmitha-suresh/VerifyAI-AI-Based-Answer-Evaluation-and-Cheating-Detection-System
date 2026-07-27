"""
Main Entry Point for AI Proctoring Web Platform FastAPI Application.
Run with: uvicorn backend.main:app --reload
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.settings import settings
from backend.core.logger import logger
from backend.services.webcam_service import webcam_service
from backend.api.routes import router as api_router
from backend.api.websocket import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler managing camera background worker threads."""
    logger.info("Initializing AI Proctoring Platform Subsystems...")
    webcam_service.start()
    yield
    logger.info("Shutting down AI Proctoring Platform Subsystems...")
    webcam_service.stop()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Enterprise-Grade FastAPI AI Proctoring & Cheating Detection Suite",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static File Directories
os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=settings.SNAPSHOT_DIR), name="snapshots")

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

# Include Router Modules
app.include_router(api_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
