"""
routers/exotel.py — Exotel webhook endpoints for phone call flow.
"""

import os
import uuid

import httpx
from fastapi import APIRouter, Form, BackgroundTasks
from fastapi.responses import PlainTextResponse

# pyrefly: ignore [missing-import]
from services import ai_service, farmer_service, pipeline_service, call_service, flag_service
# pyrefly: ignore [missing-import]
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


@router.post("/exotel/incoming")
async def incoming_call(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(default=""),
):
    """Handle incoming Exotel call — greet + start recording."""
    farmer = await farmer_service.get_or_create_farmer(From)
    
    # Initialize a new call document
    await call_service.start_call(CallSid, From, farmer.get("district"), farmer.get("village"))

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

        # Get farmer profile
        farmer = await farmer_service.get_or_create_farmer(From)

        # Transcribe with Whisper
        farmer_text = await ai_service.transcribe_audio(audio_bytes, district=farmer.get("district"))

        # Onboarding or full pipeline
        flags = []
        if not farmer.get("onboarding_complete"):
            response_text, updates = get_onboarding_response(farmer, farmer_text)
            if updates:
                await farmer_service.update_farmer(From, updates)
        else:
            context = await pipeline_service.build_context(farmer_text, farmer)
            response_text, flags = await ai_service.get_kisan_response(farmer_text, farmer, context)

        # Save conversation
        await farmer_service.save_conversation_turn(From, "farmer", farmer_text)
        await farmer_service.save_conversation_turn(From, "kisan", response_text)

        os.makedirs("static/calls", exist_ok=True)
        audio_id = CallSid or uuid.uuid4().hex[:12]
        import time
        ts = int(time.time())
        farmer_audio_path = f"static/calls/{audio_id}_farmer_{ts}.webm"
        with open(farmer_audio_path, "wb") as f:
            f.write(audio_bytes)

        # Generate TTS
        kisan_audio_path = f"static/calls/{audio_id}_kisan_{ts}.mp3"
        await ai_service.text_to_speech(response_text, kisan_audio_path)

        if CallSid:
            await call_service.append_transcript(CallSid, "farmer", farmer_text, farmer_audio_path)
            await call_service.append_transcript(CallSid, "kisan", response_text, kisan_audio_path)
            if flags:
                await flag_service.create_flags(flags, CallSid, farmer.get("district"), farmer.get("village"), farmer_audio_path)

        # We no longer cleanup the files immediately so we can view them in the dashboard

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{BASE_URL}/{kisan_audio_path}</Play>
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
    if CallSid:
        await call_service.end_call(CallSid)
    # We no longer delete mp3_path here
    return {"status": "ok"}
