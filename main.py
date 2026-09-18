"""
Project Rakshak — FastAPI Main Application Entry Point
SEOC Integrated Disaster Intelligence Backend
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ─── Logging Configuration ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("rakshak.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("rakshak.main")

# ─── Load environment config (optional .env support) ─────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional

# ─── Startup / Shutdown Lifecycle ─────────────────────────────────────────────
_background_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _background_task

    logger.info("=" * 60)
    logger.info("  RAKSHAK SEOC — Initializing Backend Systems")
    logger.info("=" * 60)

    # Initialize database
    from backend.core.database import init_db
    init_db()
    logger.info("[OK] SQLite database initialized.")

    # Start background sensor simulation loop
    from backend.tasks.background import sensor_simulation_loop
    _background_task = asyncio.create_task(sensor_simulation_loop())
    logger.info("[OK] Background sensor loop started.")

    # Pre-warm weather cache for priority cities
    logger.info("[..] Pre-warming weather cache for priority cities...")
    try:
        from backend.services.weather_api import fetch_weather
        priority_cities = ["Rudraprayag", "Chamoli", "Joshimath", "Dehradun"]
        for city in priority_cities:
            await asyncio.to_thread(fetch_weather, city)
        logger.info("[OK] Weather cache warmed for %d cities.", len(priority_cities))
    except Exception as e:
        logger.warning("[WARN] Weather pre-warm failed (will retry): %s", e)

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        logger.info("[OK] Gemini API key detected — AI features active.")
    else:
        logger.warning("[WARN] GEMINI_API_KEY not set — AI features using fallback templates.")

    logger.info("=" * 60)
    logger.info("  RAKSHAK BACKEND ONLINE — http://localhost:3000")
    logger.info("=" * 60)

    yield  # ── Application is running ──

    # Shutdown
    if _background_task:
        _background_task.cancel()
        logger.info("[OK] Background tasks stopped.")
    logger.info("RAKSHAK backend shut down cleanly.")


# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Rakshak SEOC API",
    description="Uttarakhand State Emergency Operations Centre — Integrated Disaster Intelligence Backend",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ─── CORS (allows frontend and Streamlit to talk to the API) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )

# ─── Register API Routers ─────────────────────────────────────────────────────
from backend.api.routes.state import router as state_router
from backend.api.routes.sos import router as sos_router
from backend.api.routes.simulate import router as sim_router
from backend.api.routes.alerts import router as alerts_router
from backend.api.routes.dispatch import router as dispatch_router
from backend.api.routes.ws import router as ws_router

app.include_router(state_router)
app.include_router(sos_router)
app.include_router(sim_router)
app.include_router(alerts_router)
app.include_router(dispatch_router)
app.include_router(ws_router)

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "operational",
        "service": "Rakshak SEOC Backend v2.0",
        "gemini_enabled": bool(os.environ.get("GEMINI_API_KEY")),
    }

# ─── Serve the existing HTML Frontend (must be LAST — catches all unmatched routes) ──
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.isdir(PUBLIC_DIR):
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")
    logger.info("[OK] Frontend served from: %s", PUBLIC_DIR)
else:
    logger.warning("[WARN] 'public/' directory not found — frontend not mounted.")


# ─── Direct Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3000,
        reload=False,
        log_level="info",
    )

