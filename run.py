#!/usr/bin/env python3
"""
run.py — One-command server launcher for LANTRA AI Platform.

Usage:
    python run.py

Opens:
    API  : http://127.0.0.1:8001/api/v1/
    Docs : http://127.0.0.1:8001/docs
    UI   : http://127.0.0.1:8001/ui
"""

import sys
import os
from pathlib import Path

# ─── Force UTF-8 output on Windows (emoji / Indic script safe printing) ───────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7 fallback

# ─── Ensure project root is on the Python path ────────────────────────────────
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

# ─── Load .env if present ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # python-dotenv optional

HOST      = os.environ.get("HOST",      "127.0.0.1")
PORT      = int(os.environ.get("PORT",  "8001"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")
RELOAD    = os.environ.get("RELOAD",    "true").lower() == "true"

# ─── Banner ───────────────────────────────────────────────────────────────────
print("""
╔══════════════════════════════════════════════════════════╗
║     🇮🇳  LANTRA — AI LOCALIZATION ENGINE                 ║
║         Samsung Indic Content Platform  v1.0.0           ║
╚══════════════════════════════════════════════════════════╝
""")
print(f"  🚀  Starting API server on  http://{HOST}:{PORT}")
print(f"  📖  Swagger docs          → http://{HOST}:{PORT}/docs")
print(f"  🖥️   Frontend UI           → http://{HOST}:{PORT}/ui")
print(f"  ⚙️   Reload mode           : {'ON' if RELOAD else 'OFF'}\n")

# ─── Start uvicorn ────────────────────────────────────────────────────────────
try:
    import uvicorn
except ImportError:
    print("❌  uvicorn not found. Install it with:\n    pip install uvicorn[standard]\n")
    sys.exit(1)

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host      = HOST,
        port      = PORT,
        reload    = RELOAD,
        log_level = LOG_LEVEL,
    )
