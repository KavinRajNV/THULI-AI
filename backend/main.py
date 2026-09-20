"""
KISAN.AI — Main FastAPI Application
Multilingual voice-first agricultural intelligence for Tamil Nadu farmers.
"""

import os
from dotenv import load_dotenv

# ⚠️ CRITICAL: load_dotenv() MUST run before any other imports
# because ai_service.py, weather_service.py etc. read os.getenv() at import time
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from routers import chat, admin, alerts
from Exotel import exotel
from data.loader import load_all_datasets
from scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # --- Startup ---
    print("🌾 KISAN.AI starting up...")

    sarvam_key = os.getenv("SARVAM_API_KEY", "")
    if not sarvam_key or sarvam_key == "your_sarvam_key_here":
        print("❌ WARNING: SARVAM_API_KEY is not set! STT/TTS will fail.")
    else:
        print(f"✅ Sarvam API key loaded ({sarvam_key[:8]}...)")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key or groq_key == "your_groq_key_here":
        print("❌ WARNING: GROQ_API_KEY is not set! LLM will fail.")
    else:
        print(f"✅ Groq API key loaded ({groq_key[:8]}...)")

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("❌ WARNING: DATABASE_URL is not set! Database will fail.")
    else:
        print("✅ PostgreSQL DATABASE_URL loaded")

    # Verify PostgreSQL connection
    try:
        from database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ PostgreSQL connected successfully")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")

    load_all_datasets()
    
    # Initialize Disease RAG (BGE-M3 + FAISS)
    from services.disease_service import init_models
    init_models()
    
    start_scheduler()
    print("✅ All datasets loaded. Scheduler running.")
    yield
    # --- Shutdown ---
    from database import engine
    await engine.dispose()
    print("🛑 KISAN.AI shutting down.")


app = FastAPI(
    title="KISAN.AI",
    description="Multilingual voice-first agricultural intelligence for Tamil Nadu farmers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server + production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve TTS audio files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(chat.router, tags=["Chat"])
app.include_router(exotel.router, tags=["Exotel"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(alerts.router, tags=["Alerts"])


@app.get("/ping")
async def ping():
    """Keep-alive for Render.com free tier (hit by UptimeRobot every 10 min)."""
    from datetime import datetime
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/")
async def root():
    return {
        "app": "KISAN.AI",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
        "database": "PostgreSQL",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)