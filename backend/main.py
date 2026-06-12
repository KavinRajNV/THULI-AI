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

from routers import chat, exotel, admin, alerts
from data.loader import load_all_datasets
from scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # --- Startup ---
    print("🌾 KISAN.AI starting up...")

    # Verify critical env vars
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        print("❌ WARNING: OPENAI_API_KEY is not set! GPT/Whisper/TTS will fail.")
    else:
        print(f"✅ OpenAI API key loaded ({api_key[:8]}...)")

    mongo_uri = os.getenv("MONGODB_URI", "")
    if not mongo_uri or mongo_uri == "your_mongodb_atlas_uri_here":
        print("❌ WARNING: MONGODB_URI is not set!")
    else:
        print("✅ MongoDB URI loaded")

    load_all_datasets()
    start_scheduler()
    print("✅ All datasets loaded. Scheduler running.")
    yield
    # --- Shutdown ---
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
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)