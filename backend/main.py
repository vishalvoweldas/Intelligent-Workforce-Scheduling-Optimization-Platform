"""Main FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.models.database import Base, engine
import backend.models.entities  # Ensure models are loaded

# Import API Routers
from backend.api.auth import router as auth_router
from backend.api.workforce import router as workforce_router
from backend.api.shifts import router as shifts_router
from backend.api.schedules import router as schedules_router
from backend.api.leave import router as leave_router
from backend.api.swaps import router as swaps_router
from backend.api.attendance import router as attendance_router
from backend.api.analytics import router as analytics_router
from backend.api.datasets import router as datasets_router
from backend.api.evaluations import router as evaluations_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Intelligent Workforce Scheduling & Optimization Platform",
    description="Enterprise workforce scheduling, constraint optimization (OR-Tools), simulation, and evaluation platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# Register API Routers under /api/v1
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(workforce_router, prefix=API_PREFIX)
app.include_router(shifts_router, prefix=API_PREFIX)
app.include_router(schedules_router, prefix=API_PREFIX)
app.include_router(leave_router, prefix=API_PREFIX)
app.include_router(swaps_router, prefix=API_PREFIX)
app.include_router(attendance_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)
app.include_router(datasets_router, prefix=API_PREFIX)
app.include_router(evaluations_router, prefix=API_PREFIX)

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "workforce-scheduling-platform",
        "version": "1.0.0",
        "solver": "Google OR-Tools CP-SAT"
    }

# Serve built frontend static assets if available
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_frontend_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/{catchall:path}")
    def serve_spa_fallback(catchall: str):
        # Don't intercept API routes or docs
        if catchall.startswith("api") or catchall.startswith("docs") or catchall.startswith("redoc") or catchall.startswith("openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Intelligent Workforce Scheduling Platform API is active."}
else:
    @app.get("/")
    def root():
        return {
            "message": "Intelligent Workforce Scheduling & Optimization Platform API is active.",
            "documentation": "/docs"
        }

