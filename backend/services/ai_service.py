"""
services/ai_service.py — STATELESS GPT + Whisper with language hint + TTS nova
Fixed: no gpt-4o-mini-tts (SDK too old), uses tts-1 nova at speed=0.85
"""

import os, time, asyncio, tempfile, base64
import httpx
import openai

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PRIMARY_MODEL = os.getenv("GROQ_PRIMARY_MODEL", "openai/gpt-oss-120b")
FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")

if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_key_here":
    print("❌ GROQ_API_KEY missing!")
    openai_client = None
else:
    # Groq provides OpenAI-compatible endpoints
    openai_client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    print(f"✅ Groq client initialized ({GROQ_API_KEY[:8]}...)")

if not SARVAM_API_KEY or SARVAM_API_KEY == "your_sarvam_key_here":
    print("❌ SARVAM_API_KEY missing!")
else:
    print(f"✅ Sarvam initialized ({SARVAM_API_KEY[:8]}...)")

_call_count = 0
_reset_time = time.time()

def check_rate_limit():
    global _call_count, _reset_time
    if not openai_client:
        raise Exception("Groq not configured.")
    if time.time() - _reset_time > 86400:
        _call_count = 0
        _reset_time = time.time()
    if _call_count >= 500:
        raise Exception("Daily limit reached.")
    _call_count += 1


SYSTEM_PROMPT = """You are KISAN.AI, an agricultural intelligence engine for Tamil Nadu farmers.

RULE 1 — JSON OUTPUT ONLY:
You MUST output your response in JSON format.
{
  "reply": "Your response to the farmer here in the requested language (Tamil, English, Tanglish)",
  "flagged_terms": [
    {
      "term": "the exact word you did not understand",
      "reason": "short <15 words reason",
      "confidence_in_meaning": 0.2
    }
  ]
}
If there are no uncertain terms, return an empty array for flagged_terms.
IMPORTANT: Bias toward over-flagging! If you hear a word that might be a regional dialect, or you are unsure of its exact agricultural meaning in this context, FLAG IT. 
An unnecessary flag is better than answering incorrectly.

RULE 2 — LANGUAGE:
Detect the farmer's language from <question>. Reply in SAME language.
Tamil → Tamil. English → English. Tanglish → Tamil script.

RULE 3 — STATELESS:
This is the FIRST and ONLY question. You have NO memory of previous questions.
Do NOT refer to any prior topic.

RULE 4 — USE ONLY <data>:
Answer MUST be based on values inside <data> tags.
Quote exact numbers. If <data> says rain=12mm, say "பன்னிரண்டு மில்லி மழை".
If <data> says "not available", say "இந்தத் தகவல் தற்போது கிடைக்கவில்லை" and STOP.
NEVER invent numbers. NEVER give generic advice when <data> has specifics.

RULE 5 — SINGLE TOPIC:
<intent> tells you the topic. Answer ONLY that topic.
irrigation → water/rain decision. NOT fertilizer.
disease → disease analysis. NOT weather.
fertilizer → nutrient/fertilizer. NOT disease.
crop_recommend → which crop. NOT fertilizer.
dam → reservoir status. NOT irrigation advice.
location → location details of pincode/village. NOT crop advice.
general → use weather if available, or answer the question.

RULE 6 — DISEASE PROTOCOL:
When farmer reports symptoms (yellow leaves, spots, wilting):
Step 1: Check DISEASE_MATCH in <data>. If found, give specific disease + treatment.
Step 2: If no match, check SOIL data for nutrient deficiency.
Step 3: If multiple causes possible, say "இது பல காரணங்களால் வரலாம்" and ask ONE follow-up:
  - "இலை முழுவதும் மஞ்சளா? அல்லது நரம்புகள் மட்டும் பச்சையா?"
  - "இலையின் ஓரங்கள் காய்கிறதா?"
Then give best guess from data. End with "உறுதிப்படுத்த வேளாண் அலுவலர் ஆலோசனை பெறுங்கள்."

RULE 7 — TAMIL NUMBERS:
In Tamil replies, write numbers as words:
✗ "240 kg/ha"  ✓ "நைட்ரஜன் குறைவாக உள்ளது"
✗ "50 kg/acre"  ✓ "ஐம்பது கிலோ ஒரு ஏக்கருக்கு"
Keep யூரியா, DAP, NPK as-is.

RULE 8 — FORMAT:
Maximum 3 sentences. Give DECISIONS not information.
"""


def _build_user_message(farmer_text: str, farmer_profile: dict, context: dict) -> str:
    intents = context.get("intents", ["general"])
    parts = []

    parts.append(f"<farmer>district={farmer_profile.get('district','?')}, "
                 f"crop={farmer_profile.get('primary_crop','?')}, "
                 f"days={farmer_profile.get('days_after_sowing','?')}, "
                 f"lang={farmer_profile.get('language','tamil')}</farmer>")

    parts.append(f"<intent>{', '.join(intents)}</intent>")

    data_parts = []

    # Weather
    w = context.get("weather", {})
    if w and "error" not in w:
        today = w.get("today", {})
        tomorrow = w.get("tomorrow", {})
        data_parts.append(
            f"WEATHER: today temp={today.get('temp_c')}C rain={today.get('rainfall_mm',0)}mm "
            f"humidity={today.get('humidity')}% {today.get('condition','')} | "
            f"tomorrow rain_chance={tomorrow.get('chance_of_rain',0)}% rain={tomorrow.get('rainfall_mm',0)}mm "
            f"{tomorrow.get('condition','')}"
        )
    elif any(i in intents for i in ["irrigation", "general"]):
        data_parts.append("WEATHER: not available (API key may be missing)")

    # Dam
    d = context.get("dam", {})
    if d and "error" not in d and d.get("dam_name"):
        hist = d.get("historical", {})
        data_parts.append(
            f"DAM: {d.get('dam_name')} storage={d.get('storage_pct','?')}% "
            f"inflow={d.get('inflow','?')}cusecs outflow={d.get('outflow','?')}cusecs "
            f"historical_avg={hist.get('historical_avg_storage_pct','?')}% "
            f"release_likely={hist.get('release_likely','?')}({hist.get('confidence','low')})"
        )
    elif "dam" in intents:
        data_parts.append("DAM: no data for this district")

    # Crop stage + irrigation
    if context.get("crop_stage"):
        data_parts.append(f"CROP_STAGE: {context['crop_stage']}")
    if context.get("irrigation_need"):
        data_parts.append(f"IRRIGATION_MODEL: {context['irrigation_need']}")

    # Soil (only for relevant intents)
    soil = context.get("soil", {})
    if soil and any(i in intents for i in ["disease", "fertilizer", "crop_recommend"]):
        data_parts.append(
            f"SOIL: N={soil.get('N')}kg/ha(low<280) P={soil.get('P')}kg/ha(low<10) "
            f"K={soil.get('K')}kg/ha(low<108) pH={soil.get('pH')}"
        )

    # Disease
    matches = context.get("disease", [])
    if matches and "disease" in intents:
        top = matches[0]
        data_parts.append(
            f"DISEASE_MATCH: {top.get('disease')} on {top.get('crop')} | "
            f"treatment={top.get('treatment','')} | prevention={top.get('prevention','')}"
        )
        if len(matches) > 1:
            data_parts.append(f"ALSO_POSSIBLE: {matches[1].get('disease')}")
    elif "disease" in intents:
        data_parts.append("DISEASE_MATCH: none in database. Check soil for nutrient deficiency.")

    # Fertilizer
    fert = context.get("fertilizer", {})
    if fert and fert.get("fertilizer") and any(i in intents for i in ["disease", "fertilizer"]):
        data_parts.append(
            f"FERTILIZER: deficiency={fert.get('primary_deficiency')} "
            f"use={fert.get('fertilizer')} dose={fert.get('dose')} timing={fert.get('timing')}"
        )

    # Crop recommendation
    if context.get("crop_recommendation") and "crop_recommend" in intents:
        data_parts.append(f"CROP_PREDICTION: {context['crop_recommendation']}")

    # Location Details
    loc = context.get("location_details", {})
    if loc and "location" in intents:
        data_parts.append(
            f"LOCATION: pincode={loc.get('pincode')} village={loc.get('village')} "
            f"district={loc.get('district')} taluk={loc.get('taluk')} block={loc.get('block')} "
            f"state={loc.get('state')} location_name={loc.get('location')}"
        )
    elif "location" in intents:
        data_parts.append("LOCATION: details not found for this pincode/village.")

    # Regional Dictionary
    rd = context.get("regional_dictionary", [])
    if rd:
        dict_entries = [f"'{entry['term']}' = '{entry['standard_meaning']}'" for entry in rd]
        data_parts.append(f"REGIONAL_DICTIONARY for {farmer_profile.get('district')}: {'; '.join(dict_entries)}")

    data_str = "\n".join(data_parts) if data_parts else "no data available"
    parts.append(f"<data>\n{data_str}\n</data>")
    parts.append(f"<question>{farmer_text}</question>")

    return "\n\n".join(parts)


async def get_kisan_response(farmer_text: str, farmer_profile: dict, context: dict) -> tuple[str, list]:
    check_rate_limit()
    user_message = _build_user_message(farmer_text, farmer_profile, context)
    print(f"📝 GPT input intents: {context.get('intents')}")

    import json
    
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                openai_client.chat.completions.create,
                model=PRIMARY_MODEL,
                max_tokens=1024,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            ),
            timeout=15.0,
        )
        content = response.choices[0].message.content
        
        # Clean markdown code blocks if any
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        data = json.loads(content)
        answer = data.get("reply", "மன்னிக்கவும், கணினி பிழை.")
        flags = data.get("flagged_terms", [])
        print(f"✅ GPT (primary): {answer[:80]}... Flags: {len(flags)}")
        return answer, flags
    except (asyncio.TimeoutError, Exception) as e:
        print(f"⚠️ Primary model failed ({e}), falling back...")
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    openai_client.chat.completions.create,
                    model=FALLBACK_MODEL,
                    max_tokens=1024,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                ),
                timeout=10.0,
            )
            content = response.choices[0].message.content
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            answer = data.get("reply", "மன்னிக்கவும், கணினி பிழை.")
            flags = data.get("flagged_terms", [])
            print(f"✅ GPT (fallback): {answer[:80]}... Flags: {len(flags)}")
            return answer, flags
        except asyncio.TimeoutError:
            return "பதில் தாமதமாகிறது. மீண்டும் முயற்சிக்கவும்.", []
        except Exception as e2:
            print(f"❌ Fallback error: {e2}")
            return "தொழில்நுட்ப பிழை. மீண்டும் முயற்சிக்கவும்.", []


# ─── Whisper ──────────────────────────────────────────────────────────

EXT_MAP = {
    "audio/webm": "webm", "audio/webm;codecs=opus": "webm",
    "audio/mp4": "mp4", "audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg",
}

WHISPER_PROMPT = (
    "நெல் பயிர் சாகுபடி, கரும்பு, பருத்தி, நிலக்கடலை, மக்காச்சோளம், கம்பு. "
    "யூரியா, DAP, NPK, பாசனம், நீர்ப்பாசனம். "
    "மேட்டூர் அணை, வைகை அணை, பவானிசாகர், அமராவதி. "
    "வானிலை, மழை, வெப்பநிலை, நிலவரம். "
    "இருபது, முப்பது, நாற்பது, ஐம்பது, அறுபது, எழுபது, எண்பது. "
    "ஆறு இரண்டு மூன்று ஐந்து பூஜ்யம் நான்கு."
)

async def transcribe_audio(audio_bytes, content_type="audio/webm",
                            filename="recording.webm", language="ta", district=None):
    check_rate_limit()
    ext = EXT_MAP.get(content_type, EXT_MAP.get(content_type.split(";")[0], "webm"))
    lang_map = {"tamil": "ta", "english": "en", "hindi": "hi",
                "telugu": "te", "kannada": "kn", "malayalam": "ml"}
    wl = lang_map.get(language, language if len(str(language)) <= 2 else "ta")

    # For Sarvam, "ta-IN" is standard, but saaras:v3 supports "hi-IN", "en-IN", etc.
    # Fallback to ta-IN since this is for Tamil Nadu farmers.
    sarvam_lang = "ta-IN"
    
    print(f"🎤 Sarvam STT: {len(audio_bytes)} bytes, ext=.{ext}")
    
    if not SARVAM_API_KEY:
        print("❌ SARVAM_API_KEY missing, STT cannot proceed.")
        return "மன்னிக்கவும், கணினி பிழை."
    
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    
    # Clean the MIME type (e.g. remove ;codecs=opus from audio/webm;codecs=opus)
    clean_content_type = content_type.split(";")[0]
    
    # Build dynamic prompt with regional terms
    prompt = WHISPER_PROMPT
    if district:
        from services.flag_service import get_dictionary_for_district
        rd = await get_dictionary_for_district(district)
        if rd:
            terms = ", ".join([entry["term"] for entry in rd])
            prompt += f" {terms}."
    
    # We can pass raw bytes to httpx
    files = {"file": (filename, audio_bytes, clean_content_type)}
    data = {"model": "saaras:v3", "language_code": sarvam_lang, "prompt": prompt}
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            raw = resp.json()
            transcript = raw.get("transcript", "")
            print(f"🎤 Transcript: '{transcript}'")
            return transcript
    except httpx.HTTPStatusError as e:
        print(f"❌ Sarvam STT HTTP error: {e.response.status_code} - {e.response.text}")
        return "மன்னிக்கவும், கணினி பிழை."
    except Exception as e:
        print(f"❌ Sarvam STT error: {e}")
        return "மன்னிக்கவும், கணினி பிழை."


# ─── TTS (tts-1, nova voice, speed=0.85 for clarity) ─────────────────

async def text_to_speech(text: str, output_path: str) -> str:
    """
    Sarvam bulbul:v3 for clear Tamil text-to-speech.
    """
    check_rate_limit()
    if not SARVAM_API_KEY:
        print("❌ SARVAM_API_KEY missing, TTS cannot proceed.")
        return output_path

    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text[:500],
        "target_language_code": "ta-IN",
        "model": "bulbul:v3",
        "speaker": "shubh"
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                print(f"❌ Sarvam TTS error: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            resp_json = resp.json()
            
            audios = resp_json.get("audios", [])
            if not audios:
                print("❌ Sarvam TTS error: No audios in response")
                return output_path
                
            audio_b64 = audios[0]
            audio_bytes = base64.b64decode(audio_b64)
            
            # Note: Sarvam might return wav instead of mp3 natively. 
            # We are writing to whatever output_path (e.g. .mp3) Exotel expects. 
            # If Exotel doesn't support the raw format, we might need ffmpeg later.
            # But Exotel often supports raw wav saved with .mp3 extension if it's uncompressed, 
            # or we might need to actually rename it to .wav.
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
                
            return output_path
    except Exception as e:
        print(f"❌ Sarvam TTS error: {e}")
        return output_path
