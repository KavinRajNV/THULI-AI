"""
services/ai_service.py — STATELESS GPT + Whisper with language hint + TTS nova
Fixed: no gpt-4o-mini-tts (SDK too old), uses tts-1 nova at speed=0.85
"""

import os, time, asyncio, tempfile
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY or OPENAI_API_KEY == "your_key_here":
    print("❌ OPENAI_API_KEY missing!")
    openai_client = None
else:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    print(f"✅ OpenAI client initialized ({OPENAI_API_KEY[:8]}...)")

_call_count = 0
_reset_time = time.time()

def check_rate_limit():
    global _call_count, _reset_time
    if not openai_client:
        raise Exception("OpenAI not configured.")
    if time.time() - _reset_time > 86400:
        _call_count = 0
        _reset_time = time.time()
    if _call_count >= 500:
        raise Exception("Daily limit reached.")
    _call_count += 1


SYSTEM_PROMPT = """You are KISAN.AI, an agricultural intelligence engine for Tamil Nadu farmers.

RULE 1 — LANGUAGE:
Detect the farmer's language from <question>. Reply in SAME language.
Tamil → Tamil. English → English. Tanglish → Tamil script.

RULE 2 — STATELESS:
This is the FIRST and ONLY question. You have NO memory of previous questions.
Do NOT refer to any prior topic.

RULE 3 — USE ONLY <data>:
Answer MUST be based on values inside <data> tags.
Quote exact numbers. If <data> says rain=12mm, say "பன்னிரண்டு மில்லி மழை".
If <data> says "not available", say "இந்தத் தகவல் தற்போது கிடைக்கவில்லை" and STOP.
NEVER invent numbers. NEVER give generic advice when <data> has specifics.

RULE 4 — SINGLE TOPIC:
<intent> tells you the topic. Answer ONLY that topic.
irrigation → water/rain decision. NOT fertilizer.
disease → disease analysis. NOT weather.
fertilizer → nutrient/fertilizer. NOT disease.
crop_recommend → which crop. NOT fertilizer.
dam → reservoir status. NOT irrigation advice.
general → use weather if available, or answer the question.

RULE 5 — DISEASE PROTOCOL:
When farmer reports symptoms (yellow leaves, spots, wilting):
Step 1: Check DISEASE_MATCH in <data>. If found, give specific disease + treatment.
Step 2: If no match, check SOIL data for nutrient deficiency.
Step 3: If multiple causes possible, say "இது பல காரணங்களால் வரலாம்" and ask ONE follow-up:
  - "இலை முழுவதும் மஞ்சளா? அல்லது நரம்புகள் மட்டும் பச்சையா?"
  - "இலையின் ஓரங்கள் காய்கிறதா?"
Then give best guess from data. End with "உறுதிப்படுத்த வேளாண் அலுவலர் ஆலோசனை பெறுங்கள்."

RULE 6 — TAMIL NUMBERS:
In Tamil replies, write numbers as words:
✗ "240 kg/ha"  ✓ "நைட்ரஜன் குறைவாக உள்ளது"
✗ "50 kg/acre"  ✓ "ஐம்பது கிலோ ஒரு ஏக்கருக்கு"
Keep யூரியா, DAP, NPK as-is.

RULE 7 — FORMAT:
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

    data_str = "\n".join(data_parts) if data_parts else "no data available"
    parts.append(f"<data>\n{data_str}\n</data>")
    parts.append(f"<question>{farmer_text}</question>")

    return "\n\n".join(parts)


async def get_kisan_response(farmer_text: str, farmer_profile: dict, context: dict) -> str:
    check_rate_limit()
    user_message = _build_user_message(farmer_text, farmer_profile, context)
    print(f"📝 GPT input intents: {context.get('intents')}")

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4o-mini",
                max_tokens=200,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            ),
            timeout=15.0,
        )
        answer = response.choices[0].message.content
        print(f"✅ GPT: {answer[:80]}...")
        return answer
    except asyncio.TimeoutError:
        return "பதில் தாமதமாகிறது. மீண்டும் முயற்சிக்கவும்."
    except Exception as e:
        print(f"❌ GPT error: {e}")
        return "தொழில்நுட்ப பிழை. மீண்டும் முயற்சிக்கவும்."


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
                            filename="recording.webm", language="ta"):
    check_rate_limit()
    ext = EXT_MAP.get(content_type, EXT_MAP.get(content_type.split(";")[0], "webm"))
    lang_map = {"tamil": "ta", "english": "en", "hindi": "hi",
                "telugu": "te", "kannada": "kn", "malayalam": "ml"}
    wl = lang_map.get(language, language if len(str(language)) <= 2 else "ta")

    print(f"🎤 Whisper: {len(audio_bytes)} bytes, lang={wl}, ext=.{ext}")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        def _t():
            with open(tmp_path, "rb") as f:
                return openai_client.audio.transcriptions.create(
                    model="whisper-1", file=f,
                    language=wl,
                    prompt=WHISPER_PROMPT if wl == "ta" else "",
                    temperature=0,
                )
        result = await asyncio.to_thread(_t)
        print(f"🎤 Transcript: '{result.text}'")
        return result.text
    except Exception as e:
        print(f"❌ Whisper: {e}")
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass


# ─── TTS (tts-1, nova voice, speed=0.85 for clarity) ─────────────────

async def text_to_speech(text: str, output_path: str) -> str:
    """
    tts-1 with nova voice at speed=0.85.
    Nova is the clearest voice for non-English text.
    Speed 0.85 slows it just enough to be understandable.
    """
    check_rate_limit()
    def _t():
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text[:500],
            speed=0.85,
        )
        response.stream_to_file(output_path)
        return output_path
    return await asyncio.to_thread(_t)
