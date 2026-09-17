"""
services/validation_agent.py — Async Gemini agent to validate regional terms.
"""
import os
import json
import asyncio
import google.generativeai as genai
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import async_session
from models import Flag, Call, RegionalDictionary
from datetime import datetime

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini_model = None
    print("❌ GEMINI_API_KEY missing. Validation agent disabled.")

async def process_pending_flag_group(normalized_term: str, district: str):
    """Run validation agent on a group of pending flags."""
    if not gemini_model:
        return None

    async with async_session() as session:
        result = await session.execute(
            select(Flag).where(
                Flag.normalized_term == normalized_term,
                Flag.district == district,
                Flag.status == "pending"
            ).limit(10)
        )
        occurrences = result.scalars().all()

        if not occurrences:
            return None

        context_blocks = []
        for occ in occurrences:
            call_result = await session.execute(
                select(Call).options(selectinload(Call.transcript_turns)).where(Call.call_id == occ.call_id)
            )
            call = call_result.scalars().first()
            if call and call.transcript_turns:
                transcript_text = "\n".join([f"{t.role.upper()}: {t.content}" for t in call.transcript_turns])
                context_blocks.append(f"--- Call from Village {occ.village or 'Unknown'} ---\n{transcript_text}")

        if not context_blocks:
            return None

        prompt = f"""You are an expert in Tamil Nadu agricultural dialects and linguistics.
A regional or unclear term was flagged in a farmer's conversation.

Term: '{occurrences[0].term}'
District: {district}

Here are the transcripts where this term was used:
{chr(10).join(context_blocks)}

Task: What does this term mean in standard agricultural terminology?
Provide a JSON response with:
1. "meaning": The standard Tamil/English meaning (short, <10 words).
2. "confidence": A number from 0 to 100 representing your confidence.
3. "reasoning": A brief explanation of how you deduced it from context.
"""
        try:
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            result_json = json.loads(response.text)
            
            proposed_meaning = result_json.get("meaning")
            confidence = result_json.get("confidence", 0)

            occ_ids = [occ.id for occ in occurrences]
            await session.execute(
                update(Flag).where(Flag.id.in_(occ_ids)).values(
                    ai_proposed_meaning=proposed_meaning,
                    ai_confidence=confidence,
                    status="ai-processed"
                )
            )
            await session.commit()

            if confidence >= 80:
                sim_result = await session.execute(
                    select(Flag.call_id).where(
                        Flag.normalized_term == normalized_term,
                        Flag.district == district,
                        Flag.ai_proposed_meaning == proposed_meaning,
                        Flag.ai_confidence >= 80
                    ).limit(100)
                )
                similar_calls = sim_result.scalars().all()
                distinct_calls = set(similar_calls)
                
                if len(distinct_calls) >= 3:
                    await promote_to_dictionary(normalized_term, district, proposed_meaning, confidence, "ai-verified-pending-audit")

            return result_json
        except Exception as e:
            print(f"❌ Validation Agent Error: {e}")
            return None


async def promote_to_dictionary(term: str, district: str, meaning: str, confidence: int, status: str):
    """Upsert term into regional dictionary and mark flags as resolved."""
    async with async_session() as session:
        stmt = pg_insert(RegionalDictionary).values(
            term=term,
            district=district,
            standard_meaning=meaning,
            status=status,
            last_confirmed_confidence=confidence,
            occurrence_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=['district', 'term'],
            set_={
                'standard_meaning': meaning,
                'status': status,
                'last_confirmed_confidence': confidence,
                'updated_at': datetime.utcnow(),
                'occurrence_count': RegionalDictionary.occurrence_count + 1
            }
        )
        await session.execute(stmt)
        
        await session.execute(
            update(Flag).where(
                Flag.normalized_term == term,
                Flag.district == district
            ).values(status="resolved")
        )
        await session.commit()
