"""
services/flag_service.py — Save and manage uncertain regional flags.
"""
import unicodedata
from datetime import datetime
from sqlalchemy import select, insert
from database import async_session
from models import Flag, RegionalDictionary

def normalize_term(term: str) -> str:
    """Normalize term for grouping."""
    if not term:
        return ""
    # Remove diacritics and lowercase
    nfkd_form = unicodedata.normalize('NFKD', term.strip().lower())
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

async def create_flags(flags: list, call_id: str, district: str, village: str, transcript_ref: str = None):
    """Save an array of flagged terms from a call."""
    if not flags:
        return

    docs = []
    for flag in flags:
        term = flag.get("term", "")
        if not term:
            continue
            
        docs.append({
            "call_id": call_id,
            "term": term,
            "normalized_term": normalize_term(term),
            "reason": flag.get("reason", ""),
            "confidence": flag.get("confidence_in_meaning", 0.0),
            "district": district or "Unknown",
            "village": village or "Unknown",
            "transcript_ref": transcript_ref,
            "status": "pending",
            "created_at": datetime.utcnow()
        })

    if docs:
        async with async_session() as session:
            await session.execute(insert(Flag), docs)
            await session.commit()
            
        # Trigger background validation for each unique term in this batch
        import asyncio
        from services.validation_agent import process_pending_flag_group
        unique_terms = set(doc["normalized_term"] for doc in docs)
        for ut in unique_terms:
            asyncio.create_task(process_pending_flag_group(ut, district or "Unknown"))

async def get_dictionary_for_district(district: str) -> list:
    """Fetch verified or pending-audit regional terms for a district."""
    if not district:
        return []
        
    async with async_session() as session:
        result = await session.execute(
            select(RegionalDictionary).where(
                RegionalDictionary.district == district,
                RegionalDictionary.status.in_(["verified", "ai-verified-pending-audit"])
            )
        )
        dicts = result.scalars().all()
        return [{"term": d.term, "standard_meaning": d.standard_meaning} for d in dicts]
