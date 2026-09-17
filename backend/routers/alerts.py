"""
routers/alerts.py — Alert management endpoints.
Migrated from MongoDB to PostgreSQL (SQLAlchemy async).
"""

import os
from datetime import datetime

import httpx
from fastapi import APIRouter

from sqlalchemy import select, desc
from database import async_session
from models import Farmer, AlertLog, DamStatus
from services import ai_service

router = APIRouter()

EXOTEL_SID = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN", "")
EXOTEL_VIRTUAL_NUMBER = os.getenv("EXOTEL_VIRTUAL_NUMBER", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@router.post("/api/alerts/trigger")
async def trigger_alert(body: dict):
    """
    Manually trigger alert for a district.
    Body: {district, message, alert_type}
    """
    district = body.get("district", "")
    message = body.get("message", "")
    alert_type = body.get("alert_type", "manual")

    if not district or not message:
        return {"error": "district and message required"}

    async with async_session() as session:
        # Find farmers in this district
        result = await session.execute(
            select(Farmer).where(Farmer.district.ilike(f"%{district}%"))
        )
        farmers = result.scalars().all()

        results = []
        for farmer in farmers:
            phone = farmer.phone
            if not phone:
                continue

            # Try Exotel outbound call
            success = await _make_outbound_call(phone, message)
            results.append({"phone": phone, "success": success})

        # Log the alert
        alert = AlertLog(
            district=district,
            message=message,
            alert_type=alert_type,
            farmers_contacted=len(results),
            triggered_at=datetime.utcnow(),
        )
        session.add(alert)
        await session.commit()

    return {
        "status": "sent",
        "farmers_contacted": len(results),
        "results": results[:10],  # Return first 10 for brevity
    }


@router.get("/api/alerts/check-conditions")
async def check_alert_conditions():
    """
    Check current conditions that might warrant alerts.
    Returns list of potential alerts for admin review.
    """
    potential_alerts = []

    async with async_session() as session:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        result = await session.execute(
            select(DamStatus).where(DamStatus.date == today_str)
        )
        dams = result.scalars().all()

        for dam in dams:
            storage_pct = dam.storage_percentage or 0
            outflow = dam.current_outflow_cusecs or 0

            if storage_pct and storage_pct < 20:
                potential_alerts.append({
                    "type": "low_storage",
                    "reservoir": dam.reservoir,
                    "storage_pct": storage_pct,
                    "severity": "warning",
                    "message": f"{dam.reservoir} storage critically low at {storage_pct}%",
                })

            if outflow and outflow > 5000:
                potential_alerts.append({
                    "type": "high_outflow",
                    "reservoir": dam.reservoir,
                    "outflow": outflow,
                    "severity": "alert",
                    "message": f"{dam.reservoir} releasing {outflow} cusecs — high flow alert",
                })

    return {"potential_alerts": potential_alerts, "checked_at": datetime.utcnow().isoformat()}


async def _make_outbound_call(phone: str, message: str) -> bool:
    """Make outbound call via Exotel API."""
    if not all([EXOTEL_SID, EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_VIRTUAL_NUMBER]):
        print(f"⚠️  Exotel not configured. Would call {phone}")
        return False

    try:
        # Generate TTS audio for the alert
        import uuid
        audio_id = uuid.uuid4().hex[:12]
        mp3_path = f"static/alert_{audio_id}.mp3"
        await ai_service.text_to_speech(message, mp3_path)

        # Exotel outbound call (SID in URL, API_KEY:API_TOKEN for auth)
        url = f"https://api.exotel.com/v1/Accounts/{EXOTEL_SID}/Calls/connect"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                auth=(EXOTEL_API_KEY, EXOTEL_API_TOKEN),
                data={
                    "From": phone,
                    "To": EXOTEL_VIRTUAL_NUMBER,
                    "CallerId": EXOTEL_VIRTUAL_NUMBER,
                    "Url": f"{BASE_URL}/exotel/alert-play?audio={audio_id}",
                },
            )
        return resp.status_code == 200

    except Exception as e:
        print(f"⚠️  Outbound call to {phone} failed: {e}")
        return False


@router.post("/exotel/alert-play")
async def alert_play(audio: str = ""):
    """Exotel callback to play alert audio."""
    from fastapi.responses import PlainTextResponse
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{BASE_URL}/static/alert_{audio}.mp3</Play>
</Response>"""
    return PlainTextResponse(xml, media_type="application/xml")
