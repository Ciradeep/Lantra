"""
api/server.py
=============
FastAPI application entry point for the LANTRA Localization API.

Run:
    python run.py
    # OR directly:
    uvicorn api.server:app --reload --port 8001

Endpoints:
    http://127.0.0.1:8001/api/v1/       → API info
    http://127.0.0.1:8001/docs          → Interactive Swagger UI
    http://127.0.0.1:8001/ui            → Frontend UI
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import router


# ─── Lifespan (startup/shutdown) ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the localizer on startup so first request is fast."""
    print("\n🚀 LANTRA API starting up…")
    from api.routes import get_localizer
    get_localizer()  # Pre-initialize
    print("✅ Localization engine ready. Serving requests.")
    print("📖 Swagger docs  → http://127.0.0.1:8001/docs")
    print("🖥️  Frontend UI   → http://127.0.0.1:8001/ui\n")
    yield
    print("👋 API shutting down.")


# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title        = "LANTRA — Indic Content Localization API",
    description  = (
        "🇮🇳 A production-ready API to translate, transliterate, and culturally adapt "
        "English digital content into 10 major Indian languages. "
        "Powered by IndicTrans2, Google Translate, and gTTS."
    ),
    version      = "1.0.0",
    contact      = {
        "name":  "Samsung Indic AI Platform",
        "email": "indic-ai@samsung.com",
    },
    license_info = {"name": "MIT"},
    lifespan     = lifespan,
)

# ─── CORS — Allow all origins (restrict in production) ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── Mount API routes (MUST come before StaticFiles) ─────────────────────────
# IMPORTANT: The API router is mounted first. StaticFiles must be mounted
# last because a wildcard StaticFiles mount would intercept all requests
# including /api/v1/* if mounted at "/".
app.include_router(router, prefix="/api/v1")

# ─── Serve frontend as static files at /ui (NOT at /) ────────────────────────
# Mounted at /ui so it does NOT conflict with /api/v1 routes or /docs.
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


# ─── Root redirect — redirect / to /docs ─────────────────────────────────────
@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root to API docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host      = "127.0.0.1",
        port      = 8001,
        reload    = True,
        log_level = "info",
    )
