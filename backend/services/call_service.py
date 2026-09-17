"""
services/call_service.py — Manage phone calls and transcript persistence.
"""
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import async_session
from models import Call, CallTranscriptTurn

async def start_call(call_id: str, phone: str, district: str = None, village: str = None):
    """Create a new call document."""
    async with async_session() as session:
        stmt = pg_insert(Call).values(
            call_id=call_id,
            phone=phone,
            district=district,
            village=village,
            created_at=datetime.utcnow(),
            status="in-progress"
        ).on_conflict_do_nothing(index_elements=['call_id'])
        
        await session.execute(stmt)
        await session.commit()

async def append_transcript(call_id: str, role: str, content: str, audio_ref: str = None):
    """Append a turn to the call's transcript."""
    async with async_session() as session:
        result = await session.execute(select(Call).where(Call.call_id == call_id))
        call = result.scalars().first()
        if call:
            turn = CallTranscriptTurn(
                call_db_id=call.id,
                role=role,
                content=content,
                audio_ref=audio_ref,
                timestamp=datetime.utcnow()
            )
            session.add(turn)
            await session.commit()

async def end_call(call_id: str):
    """Mark a call as completed."""
    async with async_session() as session:
        stmt = update(Call).where(Call.call_id == call_id).values(status="completed")
        await session.execute(stmt)
        await session.commit()
