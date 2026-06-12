"""
routers/exotel.py — Exotel webhook endpoints for phone call flow.
"""

import os
import uuid

import httpx
from fastapi import APIRouter, Form, BackgroundTasks
from fastapi.responses import PlainTextResponse

from services import ai_service, farmer_service, pipeline_service
from services.farmer_service import get_onboarding_response

router = APIRouter()

# ─── Exotel credentials ──────────────────────────────────────────────
# SID           → Account SID (used in API URL path)
# API_KEY       → Basic Auth username
# API_TOKEN     → Basic Auth password
# VIRTUAL_NUMBER → The Exotel phone number farmers call
EXOTEL_SID = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN", "")
EXOTEL_VIRTUAL_NUMBER = os.getenv("EXOTEL_VIRTUAL_NUMBER", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _cleanup_file(path: str):
    """Background task to delete audio file."""
    import time
    time.sleep(300)  # 5 minutes
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@router.post("/exotel/incoming")
async def incoming_call(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(default=""),
):
    """Handle incoming Exotel call — greet + start recording."""
    farmer = await farmer_service.get_or_create_farmer(From)

    if not farmer.get("onboarding_complete"):
        greeting = (
            "வணக்கம்! நான் KISAN AI. உங்கள் வேளாண் உதவியாளர். "
            "உங்கள் பின்கோடு அல்லது ஊர் பெயர் சொல்லுங்கள்."
        )
    else:
        crop = farmer.get("primary_crop", "பயிர்")
        greeting = f"வணக்கம்! உங்கள் {crop} பயிருக்கு இன்று என்ன கேள்வி?"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="female" language="ta-IN">{greeting}</Say>
  <Record action="{BASE_URL}/exotel/process"
          maxLength="30"
          finishOnKey="#"
          playBeep="true"
          transcribe="false"/>
</Response>"""
    return PlainTextResponse(xml, media_type="application/xml")


@router.post("/exotel/process")
async def process_recording(
    background_tasks: BackgroundTasks,
    RecordingUrl: str = Form(...),
    From: str = Form(...),
    CallSid: str = Form(default=""),
    RecordingDuration: str = Form(default="0"),
):
    """Process farmer's voice recording: transcribe → pipeline → respond."""
    # Guard: ignore empty/very short recordings
    try:
        duration = int(RecordingDuration)
    except ValueError:
        duration = 0

    if duration < 2:
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="ta-IN">மீண்டும் சொல்லுங்கள்.</Say>
  <Record action="{BASE_URL}/exotel/process"
          maxLength="30"
          finishOnKey="#"
          playBeep="true"/>
</Response>"""
        return PlainTextResponse(xml, media_type="application/xml")

    try:
        # Download audio from Exotel (Basic Auth = API_KEY : API_TOKEN)
        async with httpx.AsyncClient(timeout=15) as client:
            audio_resp = await client.get(
                RecordingUrl,
                auth=(EXOTEL_API_KEY, EXOTEL_API_TOKEN),
            )
        audio_bytes = audio_resp.content

        # Transcribe with Whisper
        farmer_text = await ai_service.transcribe_audio(audio_bytes)

        # Get farmer profile
        farmer = await farmer_service.get_or_create_farmer(From)

        # Onboarding or full pipeline
        if not farmer.get("onboarding_complete"):
            response_text, updates = get_onboarding_response(farmer, farmer_text)
            if updates:
                await farmer_service.update_farmer(From, updates)
        else:
            context = await pipeline_service.build_context(farmer_text, farmer)
            response_text = await ai_service.get_kisan_response(farmer_text, farmer, context)

        # Save conversation
        await farmer_service.save_conversation_turn(From, "farmer", farmer_text)
        await farmer_service.save_conversation_turn(From, "kisan", response_text)

        # Generate TTS
        audio_id = CallSid or uuid.uuid4().hex[:12]
        mp3_path = f"static/{audio_id}.mp3"
        await ai_service.text_to_speech(response_text, mp3_path)

        # Schedule cleanup
        background_tasks.add_task(_cleanup_file, mp3_path)

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{BASE_URL}/{mp3_path}</Play>
  <Record action="{BASE_URL}/exotel/process"
          maxLength="30"
          finishOnKey="#"
          playBeep="true"/>
</Response>"""
        return PlainTextResponse(xml, media_type="application/xml")

    except Exception as e:
        print(f"⚠️  Exotel processing error: {e}")
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="ta-IN">மன்னிக்கவும், தொழில்நுட்ப பிழை. மீண்டும் முயற்சிக்கவும்.</Say>
  <Record action="{BASE_URL}/exotel/process"
          maxLength="30"
          finishOnKey="#"
          playBeep="true"/>
</Response>"""
        return PlainTextResponse(xml, media_type="application/xml")


@router.post("/exotel/status")
async def call_status(
    CallSid: str = Form(default=""),
    Status: str = Form(default=""),
):
    """Handle call completion — cleanup audio files."""
    mp3_path = f"static/{CallSid}.mp3"
    try:
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
    except Exception:
        pass
    return {"status": "ok"}
