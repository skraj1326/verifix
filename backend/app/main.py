"""Main FastAPI Application for AstrixCore Verification AI."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import (
    projects,
    rtl_analysis,
    verification,
    simulation,
    coverage,
    analysis,
    ai_agents,
    spec_analysis,
    rtl_hierarchy,
    coverage_dashboard,
    reports,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings.ensure_storage_dirs()
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing without DB): {e}")
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-assisted verification from RTL to coverage closure.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

# Routes
API_PREFIX = settings.API_PREFIX
app.include_router(projects.router, prefix=API_PREFIX, tags=["Projects"])
app.include_router(rtl_analysis.router, prefix=API_PREFIX, tags=["RTL Analysis"])
app.include_router(rtl_hierarchy.router, prefix=API_PREFIX, tags=["RTL Hierarchy"])
app.include_router(verification.router, prefix=API_PREFIX, tags=["Verification"])
app.include_router(simulation.router, prefix=API_PREFIX, tags=["Simulation"])
app.include_router(coverage.router, prefix=API_PREFIX, tags=["Coverage"])
app.include_router(coverage_dashboard.router, prefix=API_PREFIX, tags=["Coverage Dashboard"])
app.include_router(reports.router, prefix=API_PREFIX, tags=["Reports"])
app.include_router(analysis.router, prefix=API_PREFIX, tags=["Analysis"])
app.include_router(ai_agents.router, prefix=API_PREFIX, tags=["AI Agents"])
app.include_router(spec_analysis.router, prefix=API_PREFIX, tags=["Specification"])


# ─── WebSocket for real-time updates ──────────────────────────────────

class ConnectionManager:
    """Manage WebSocket connections."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        await manager.send_message(websocket, {
            "type": "connected",
            "data": {"app": settings.APP_NAME, "version": settings.APP_VERSION},
        })
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await manager.send_message(websocket, {
                    "type": "pong",
                    "data": {"time": asyncio.get_event_loop().time()},
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": "AI-assisted verification from RTL to coverage closure.",
        "status": "running",
"endpoints": {
                "docs": "/docs",
                "projects": f"{API_PREFIX}/projects",
                "rtl_analysis": f"{API_PREFIX}/rtl/analyze",
                "rtl_hierarchy": f"{API_PREFIX}/rtl/hierarchy",
                "verification_plan": f"{API_PREFIX}/verification/plan",
                "assertions": f"{API_PREFIX}/verification/assertions",
                "tests": f"{API_PREFIX}/verification/tests",
                "coverage": f"{API_PREFIX}/coverage/analyze",
                "coverage_dashboard": f"{API_PREFIX}/coverage/dashboard",
                "reports": f"{API_PREFIX}/reports",
                "failure_analysis": f"{API_PREFIX}/failure-analysis",
                "spec_analysis": f"{API_PREFIX}/spec/analyze",
                "websocket": "/ws",
            },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
