from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers.analysis import router as analysis_router
from app.routers.metadata import router as metadata_router
from app.routers.system import router as system_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Backend service for Chicago crime data analysis. "
        "Provides metadata, quality checks, analysis datasets, and text conclusions."
    ),
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(metadata_router)
app.include_router(analysis_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/dashboard", tags=["frontend"])
def dashboard() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend assets not found")
    return FileResponse(index_file)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "message": "Crime Analytics API is running.",
        "docs": "/docs",
        "redoc": "/redoc",
    }
