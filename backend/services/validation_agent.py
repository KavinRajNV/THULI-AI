"""
services/validation_agent.py — Async Gemini agent to validate regional terms.
"""
import os
import json
import asyncio
import google.generativeai as genai
from services.db import flags_col, regional_dictionary_col, calls_col
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

    # Fetch all pending occurrences
    occurrences = await flags_col.find({
        "normalized_term": normalized_term,
        "district": district,
        "status": "pending"
    }).to_list(length=10)

    if not occurrences:
        return None

    # Gather transcripts
    context_blocks = []
    for occ in occurrences:
        call = await calls_col.find_one({"call_id": occ["call_id"]})
        if call and call.get("transcript"):
            transcript_text = "\n".join([f"{t['role'].upper()}: {t['content']}" for t in call["transcript"]])
            context_blocks.append(f"--- Call from Village {occ.get('village', 'Unknown')} ---\n{transcript_text}")

    if not context_blocks:
        return None

    prompt = f"""You are an expert in Tamil Nadu agricultural dialects and linguistics.
A regional or unclear term was flagged in a farmer's conversation.

Term: '{occurrences[0]['term']}'
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
        result = json.loads(response.text)
        
        proposed_meaning = result.get("meaning")
        confidence = result.get("confidence", 0)

        # Update the pending flags with the AI's proposal
        await flags_col.update_many(
            {"_id": {"$in": [occ["_id"] for occ in occurrences]}},
            {"$set": {
                "ai_proposed_meaning": proposed_meaning,
                "ai_confidence": confidence,
                "status": "ai-processed"
            }}
        )

        # Check for auto-promotion
        # Count how many distinct calls resulted in this SAME meaning with confidence > 80
        if confidence >= 80:
            similar_processed = await flags_col.find({
                "normalized_term": normalized_term,
                "district": district,
                "ai_proposed_meaning": proposed_meaning,
                "ai_confidence": {"$gte": 80}
            }).to_list(length=100)

            distinct_calls = set([doc["call_id"] for doc in similar_processed])
            if len(distinct_calls) >= 3:
                # Auto-promote!
                await promote_to_dictionary(normalized_term, district, proposed_meaning, confidence, "ai-verified-pending-audit")

        return result
    except Exception as e:
        print(f"❌ Validation Agent Error: {e}")
        return None


async def promote_to_dictionary(term: str, district: str, meaning: str, confidence: int, status: str):
    """Upsert term into regional dictionary and mark flags as resolved."""
    # Insert or update dictionary
    await regional_dictionary_col.update_one(
        {"term": term, "district": district},
        {"$set": {
            "standard_meaning": meaning,
            "status": status,
            "last_confirmed_confidence": confidence,
            "updated_at": datetime.utcnow()
        }, "$inc": {"occurrence_count": 1}, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    # Mark all related flags as resolved
    await flags_col.update_many(
        {"normalized_term": term, "district": district},
        {"$set": {"status": "resolved"}}
    )
