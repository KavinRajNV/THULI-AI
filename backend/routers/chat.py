"""
routers/chat.py — Web UI endpoints with TTS error handling.
TTS failure must NOT block the response — send text even if audio fails.
"""

import os, uuid
from fastapi import APIRouter, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from services import ai_service, farmer_service, pipeline_service
from services.farmer_service import get_onboarding_response
import asyncio

router = APIRouter()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _audio_url(req: Request, path: str) -> str:
    return f"{req.base_url}{path}"


def _profile(f: dict) -> dict:
    return {
        "district": f.get("district"), "crop": f.get("primary_crop"),
        "days": f.get("days_after_sowing"),
        "lat": f.get("lat"), "lon": f.get("lon"),
        "onboarding_complete": f.get("onboarding_complete", False),
        "language": f.get("language", "tamil"),
    }


async def _safe_tts(text: str, request: Request) -> str | None:
    """Generate TTS with timeout. Returns audio URL or None on failure."""
    try:
        aid = uuid.uuid4().hex[:12]
        wav = f"static/{aid}.wav"
        await asyncio.wait_for(
            ai_service.text_to_speech(text, wav),
            timeout=10.0,
        )
        return _audio_url(request, wav)
    except asyncio.TimeoutError:
        print("⚠️ TTS timed out (10s)")
        return None
    except Exception as e:
        print(f"⚠️ TTS failed: {e}")
        return None


@router.post("/api/chat/text")
async def text_chat(request: Request, body: dict):
    phone = body.get("phone", "web_demo")
    message = body.get("message", "").strip()
    language = body.get("language", "tamil")
    if not message:
        return JSONResponse({"error": "Empty"}, status_code=400)

    farmer = await farmer_service.get_or_create_farmer(phone)
    if language and language != farmer.get("language"):
        await farmer_service.update_farmer(phone, {"language": language})
        farmer["language"] = language

    if not farmer.get("onboarding_complete"):
        response_text, updates = get_onboarding_response(farmer, message)
        if updates:
            await farmer_service.update_farmer(phone, updates)
            farmer.update(updates)
    else:
        context = await pipeline_service.build_context(message, farmer)
        response_text = await ai_service.get_kisan_response(message, farmer, context)

    await farmer_service.save_conversation_turn(phone, "farmer", message)
    await farmer_service.save_conversation_turn(phone, "kisan", response_text)

    audio_url = await _safe_tts(response_text, request)

    return {"response_text": response_text, "audio_url": audio_url, "farmer_profile": _profile(farmer)}


@router.post("/api/chat/voice")
async def voice_chat(request: Request, audio: UploadFile,
                     phone: str = Form(default="web_demo"),
                     language: str = Form(default="tamil")):
    audio_bytes = await audio.read()
    if len(audio_bytes) < 500:
        return JSONResponse({"error": "Too short"}, status_code=400)

    farmer = await farmer_service.get_or_create_farmer(phone)
    if language:
        await farmer_service.update_farmer(phone, {"language": language})
        farmer["language"] = language

    transcript = await ai_service.transcribe_audio(
        audio_bytes, audio.content_type or "audio/webm",
        audio.filename or "recording.webm", language=language,
    )

    if not farmer.get("onboarding_complete"):
        response_text, updates = get_onboarding_response(farmer, transcript)
        if updates:
            await farmer_service.update_farmer(phone, updates)
            farmer.update(updates)
    else:
        context = await pipeline_service.build_context(transcript, farmer)
        response_text = await ai_service.get_kisan_response(transcript, farmer, context)

    await farmer_service.save_conversation_turn(phone, "farmer", transcript)
    await farmer_service.save_conversation_turn(phone, "kisan", response_text)

    # TTS with timeout — NEVER block the response
    audio_url = await _safe_tts(response_text, request)

    return {
        "transcript": transcript, "response_text": response_text,
        "audio_url": audio_url, "farmer_profile": _profile(farmer),
    }


@router.post("/api/chat/reset")
async def reset_session(body: dict):
    phone = body.get("phone", "")
    if phone:
        await farmer_service.reset_farmer(phone)
    return {"status": "reset"}


@router.get("/api/farmer/{phone}")
async def get_farmer_profile(phone: str):
    f = await farmer_service.get_or_create_farmer(phone)
    f.pop("_id", None)
    return f
