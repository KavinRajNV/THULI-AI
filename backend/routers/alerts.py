"""
routers/alerts.py — Alert management endpoints.
"""

import os
from datetime import datetime

import httpx
from fastapi import APIRouter

from services.db import farmers_col, alert_log_col, dam_status_col
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

    # Find farmers in this district
    farmers = await farmers_col.find(
        {"district": {"$regex": district, "$options": "i"}}
    ).to_list(length=500)

    results = []
    for farmer in farmers:
        phone = farmer.get("phone", "")
        if not phone:
            continue

        # Try Exotel outbound call
        success = await _make_outbound_call(phone, message)
        results.append({"phone": phone, "success": success})

    # Log the alert
    await alert_log_col.insert_one({
        "district": district,
        "message": message,
        "alert_type": alert_type,
        "farmers_contacted": len(results),
        "triggered_at": datetime.utcnow(),
    })

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

    # Check dam conditions
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    dams = await dam_status_col.find({"date": today_str}).to_list(length=50)

    for dam in dams:
        storage_pct = dam.get("storage_percentage", 0)
        outflow = dam.get("current_outflow_cusecs", 0)

        if storage_pct and storage_pct < 20:
            potential_alerts.append({
                "type": "low_storage",
                "reservoir": dam.get("reservoir"),
                "storage_pct": storage_pct,
                "severity": "warning",
                "message": f"{dam.get('reservoir')} storage critically low at {storage_pct}%",
            })

        if outflow and outflow > 5000:
            potential_alerts.append({
                "type": "high_outflow",
                "reservoir": dam.get("reservoir"),
                "outflow": outflow,
                "severity": "alert",
                "message": f"{dam.get('reservoir')} releasing {outflow} cusecs — high flow alert",
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
