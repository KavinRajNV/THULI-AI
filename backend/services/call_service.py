"""
services/call_service.py — Manage phone calls and transcript persistence.
"""
from datetime import datetime
from services.db import calls_col

async def start_call(call_id: str, phone: str, district: str = None, village: str = None):
    """Create a new call document."""
    call = {
        "call_id": call_id,
        "phone": phone,
        "district": district,
        "village": village,
        "transcript": [],
        "created_at": datetime.utcnow(),
        "status": "in-progress"
    }
    await calls_col.update_one(
        {"call_id": call_id},
        {"$setOnInsert": call},
        upsert=True
    )

async def append_transcript(call_id: str, role: str, content: str, audio_ref: str = None):
    """Append a turn to the call's transcript."""
    turn = {
        "role": role,
        "content": content,
        "audio_ref": audio_ref,
        "timestamp": datetime.utcnow()
    }
    await calls_col.update_one(
        {"call_id": call_id},
        {"$push": {"transcript": turn}}
    )

async def end_call(call_id: str):
    """Mark a call as completed."""
    await calls_col.update_one(
        {"call_id": call_id},
        {"$set": {"status": "completed"}}
    )
