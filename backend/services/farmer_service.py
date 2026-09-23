"""
services/farmer_service.py — Profile + onboarding.
Handles ALL Tamil number variants Whisper produces.
"""

import re
from datetime import datetime, timedelta
from sqlalchemy import select, insert, update, delete
from database import async_session
from models import Farmer, ConversationTurn
from services.location_service import resolve_location, extract_pincode, extract_district_name

# ─── CRUD ─────────────────────────────────────────────────────────────

async def get_or_create_farmer(phone: str) -> dict:
    async with async_session() as session:
        result = await session.execute(select(Farmer).where(Farmer.phone == phone))
        farmer = result.scalars().first()
        if not farmer:
            farmer = Farmer(
                phone=phone,
                language="tamil",
                onboarding_complete=False,
                created_at=datetime.utcnow()
            )
            session.add(farmer)
            await session.commit()
            await session.refresh(farmer)
            
        farmer_dict = farmer.to_dict()
        
        # Only include turns from the last 30 minutes to isolate the current chat session
        thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
        turns_result = await session.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.farmer_id == farmer.id,
                ConversationTurn.timestamp >= thirty_mins_ago
            )
            .order_by(ConversationTurn.timestamp.asc())
        )
        turns = turns_result.scalars().all()
        farmer_dict["conversation_history"] = [
            {"role": t.role, "content": t.content, "timestamp": t.timestamp} for t in turns
        ]
        return farmer_dict

async def update_farmer(phone: str, updates: dict):
    async with async_session() as session:
        if 'lat' in updates and 'lon' in updates and updates['lat'] is not None and updates['lon'] is not None:
            updates['geom'] = f"SRID=4326;POINT({updates['lon']} {updates['lat']})"
        stmt = update(Farmer).where(Farmer.phone == phone).values(**updates)
        await session.execute(stmt)
        await session.commit()

async def save_conversation_turn(phone: str, role: str, content: str):
    async with async_session() as session:
        result = await session.execute(select(Farmer).where(Farmer.phone == phone))
        farmer = result.scalars().first()
        if not farmer:
            return
            
        new_turn = ConversationTurn(
            farmer_id=farmer.id,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        session.add(new_turn)
        farmer.last_called = datetime.utcnow()
        
        turns_result = await session.execute(
            select(ConversationTurn)
            .where(ConversationTurn.farmer_id == farmer.id)
            .order_by(ConversationTurn.timestamp.asc())
        )
        turns = turns_result.scalars().all()
        if len(turns) >= 10:
            for t in turns[:len(turns)-9]:
                await session.delete(t)
                
        await session.commit()

async def reset_farmer(phone: str):
    async with async_session() as session:
        await session.execute(delete(Farmer).where(Farmer.phone == phone))
        await session.commit()


# ─── COMPREHENSIVE Tamil number mapping ───────────────────────────────
# Includes every variant Whisper actually produces

SINGLE_DIGITS = {
    # Tamil formal
    "பூஜ்யம்": 0, "சுழி": 0, "பூஜியம்": 0, "சுழியம்": 0, "பூஜ்ஜியம்": 0,
    "ஒன்று": 1, "ஒண்ணு": 1, "ஒன்னு": 1, "ஒரு": 1,
    "இரண்டு": 2, "ரெண்டு": 2, "ரண்டு": 2, "இரண்ட": 2,
    "மூன்று": 3, "மூணு": 3, "மூனு": 3,
    "நான்கு": 4, "நாலு": 4, "நான்லு": 4, "நால": 4, "நாங்கு": 4,
    "ஐந்து": 5, "அஞ்சு": 5, "அஞ்ச": 5, "ஐஞ்சு": 5,
    "ஆறு": 6, "ஆற": 6,
    "ஏழு": 7, "ஏழ": 7,
    "எட்டு": 8, "எட்ட": 8,
    "ஒன்பது": 9, "ஒம்போது": 9, "ஒம்பது": 9,
    # English/borrowed words Whisper produces
    "ஜீரோ": 0, "zero": 0, "சீரோ": 0,
    "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    # Tanglish
    "onnu": 1, "rendu": 2, "moonu": 3, "naalu": 4, "anju": 5,
    "aaru": 6, "ezhu": 7, "ettu": 8, "ombodu": 9, "poojiyam": 0,
    "jeero": 0, "zero": 0,
    # Whisper misheard
    "சைபர்": 0,
    # Colloquial joined suffixes (e.g., இருபத் + தஞ்சு = 25)
    "தஞ்சு": 5, "தாறு": 6, "தேழு": 7, "தெட்டு": 8, "தொன்பது": 9, "தொண்ணூறு": 9, "தொம்பது": 9,
}

COMPOUND_NUMBERS = {
    # Tamil formal
    "பத்து": 10,
    "இருபது": 20, "இருபத்": 20, "இருபத்தி": 20,
    "முப்பது": 30, "முப்பத்": 30, "முப்பத்தி": 30,
    "நாற்பது": 40, "நாற்பத்": 40, "நாற்பத்தி": 40,
    "ஐம்பது": 50, "ஐம்பத்": 50, "ஐம்பத்தி": 50,
    "அறுபது": 60, "அறுபத்": 60, "அறுபத்தி": 60,
    "எழுபது": 70, "எழுபத்": 70, "எழுபத்தி": 70,
    "எண்பது": 80, "எண்பத்": 80, "எண்பத்தி": 80,
    "தொண்ணூறு": 90, "தொண்ணூற்": 90, "தொண்ணூற்றி": 90,
    "நூறு": 100,
    # COLLOQUIAL variants Whisper actually produces
    "நாப்பது": 40, "நாப்பத்": 40, "நாப்பத்தி": 40,
    "அம்பது": 50, "அம்பத்": 50, "அம்பத்தி": 50,
    "எம்பது": 80, "எம்பத்": 80, "எம்பத்தி": 80,
    # Tanglish
    "pathu": 10, "irubathu": 20, "irupathu": 20,
    "muppathu": 30, "naarpathu": 40, "naappathu": 40,
    "aimbathu": 50, "arupathu": 60, "ezhupathu": 70,
    "enbathu": 80, "thonnuru": 90,
    # English
    "ten": 10, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100,
}

# Connectors that join tens and units (e.g., இருபத்து + ஐந்து -> இருபத்தஞ்சு where த் is the connector)
CONNECTORS = ["த்தி", "த்து", "த்", "தி", "ய", "யி", "and", "ti", "thi"]


def _text_to_number(text: str) -> int | None:
    """Convert ANY Tamil/English number variant → int."""
    text = text.strip()
    # Direct digits first
    digits = re.findall(r"\d+", text)
    if digits:
        return int(digits[0])

    text_lower = text.lower()
    # Remove common filler words
    for filler in ["நாள்", "நாள்.", "நாட்கள்", "days", "day", "ஆகிறது", "ஆக்கிறது",
                    "ஆச்சு", "ஆகுது", "ஆச்சிர்", "ஆச்சிர்.", "ஆச்சு.", "நாள"]:
        text_lower = text_lower.replace(filler, "").strip()

    # Check compounds (longest first)
    for word, val in sorted(COMPOUND_NUMBERS.items(), key=lambda x: -len(x[0])):
        if word in text_lower:
            remainder = text_lower.replace(word, "").strip()
            # Remove connectors
            remainder = re.sub(r"^(தி|த்தி|ti|thi|and|ய|யி)\s*", "", remainder).strip()
            if remainder:
                for dw, dv in sorted(SINGLE_DIGITS.items(), key=lambda x: -len(x[0])):
                    if dw in remainder:
                        return val + dv
            return val

    # Check singles
    for word, val in sorted(SINGLE_DIGITS.items(), key=lambda x: -len(x[0])):
        if word in text_lower:
            return val
    return None


def _text_to_pincode(text: str) -> str | None:
    """Extract 6-digit pincode from spoken Tamil/English digits."""
    # Already has 6 digits?
    existing = re.findall(r"\d{6}", text)
    if existing:
        return existing[0]

    # Split and convert each word
    words = re.split(r"[\s,.\-;:]+", text.strip())
    digits = []
    for w in words:
        w_clean = w.strip().lower()
        if not w_clean:
            continue
        if w_clean.isdigit():
            digits.extend(list(w_clean))
            continue
        # Check single digit map (longest match first)
        matched = False
        for nw, nv in sorted(SINGLE_DIGITS.items(), key=lambda x: -len(x[0])):
            if nw in w_clean or w_clean in nw:
                digits.append(str(nv))
                matched = True
                break
        if not matched:
            print(f"   ⚠️ Pincode word not recognized: '{w_clean}'")

    result = "".join(digits)
    print(f"   🔢 Pincode conversion: '{text}' → '{result}' ({len(result)} digits)")
    if len(result) == 6:
        return result
    if len(result) > 6:
        return result[:6]
    return None


# ─── Crop mapping ─────────────────────────────────────────────────────

CROP_MAP = {
    # Tamil (including Whisper variants and misspellings)
    "நெல்": "rice", "நெல": "rice", "நில்": "rice", "நெல்லு": "rice",
    "நெற்": "rice", "பயர்": "rice",  # Whisper sometimes adds பயர்
    "கரும்பு": "sugarcane", "பருத்தி": "cotton",
    "நிலக்கடலை": "groundnut", "மக்காச்சோளம்": "maize",
    "கோதுமை": "wheat", "சோளம்": "sorghum", "கம்பு": "pearl millet",
    "தக்காளி": "tomato", "வெங்காயம்": "onion", "கத்தரி": "brinjal",
    "மிளகாய்": "chilli", "வாழை": "banana", "தேங்காய்": "coconut",
    "உளுந்து": "blackgram", "பயறு": "greengram", "துவரை": "redgram",
    # English
    "rice": "rice", "paddy": "rice", "sugarcane": "sugarcane",
    "cotton": "cotton", "groundnut": "groundnut", "peanut": "groundnut",
    "maize": "maize", "corn": "maize", "wheat": "wheat",
    "sorghum": "sorghum", "millet": "pearl millet",
    "tomato": "tomato", "onion": "onion", "brinjal": "brinjal",
    "chilli": "chilli", "banana": "banana", "coconut": "coconut",
    # Tanglish
    "nel": "rice", "nell": "rice", "nellu": "rice", "nil": "rice",
    "nill": "rice", "nel payir": "rice",
    "karumbu": "sugarcane", "karambu": "sugarcane",
    "paruthi": "cotton", "nilakadalai": "groundnut",
    "cholam": "sorghum", "kambu": "pearl millet",
    "thakkali": "tomato", "vengayam": "onion",
    "kathiri": "brinjal", "milagai": "chilli",
    "vazhai": "banana", "thengai": "coconut",
}


# ─── Onboarding ───────────────────────────────────────────────────────

def get_onboarding_response(farmer: dict, user_text: str) -> tuple[str, dict]:
    updates = {}
    lang = farmer.get("language", "tamil")

    # ─── Step 1: Location ─────────
    if not farmer.get("district"):
        pincode = extract_pincode(user_text)
        if not pincode:
            pincode = _text_to_pincode(user_text)
        district_name = extract_district_name(user_text)

        location = {}
        if pincode:
            location = resolve_location(pincode=pincode)
        elif district_name:
            location = resolve_location(village_name=district_name)
        else:
            location = resolve_location(village_name=user_text.strip())

        if location.get("district"):
            updates.update({
                "district": location["district"],
                "village": location.get("village"),
                "lat": location.get("lat"),
                "lon": location.get("lon"),
            })
            if pincode:
                updates["pincode"] = pincode
            d = location["district"]
            v = location.get("village")
            loc_display = f"{d}, {v}" if v and v != "Not available" else d
            print(f"✅ Onboard: district={d}, village={v}, lat={location.get('lat')}, lon={location.get('lon')}")
            msgs = {
                "english": f"Thank you! {loc_display} registered. What crop are you growing?",
                "hindi": f"धन्यवाद! {loc_display} दर्ज। आप कौन सी फसल उगा रहे हैं?",
            }
            return msgs.get(lang, f"நன்றி! {loc_display} பதிவு. என்ன பயிர் சாகுபடி செய்கிறீர்கள்?"), updates
        else:
            return ("அந்த இடம் கிடைக்கவில்லை. 6 இலக்க பின்கோடு சொல்லுங்கள். உதாரணம்: 623504"
                    if lang != "english" else "Location not found. Say your 6-digit pincode."), {}

    # ─── Step 2: Crop ─────────
    if not farmer.get("primary_crop"):
        crop = _extract_crop(user_text)
        if crop:
            updates["primary_crop"] = crop
            return (f"{crop} பயிர் பதிவு. நடவு எத்தனை நாள் ஆச்சு?"
                    if lang != "english" else f"{crop} registered. Days since sowing?"), updates
        else:
            return ("என்ன பயிர்? நெல், கரும்பு, பருத்தி, நிலக்கடலை, கம்பு"
                    if lang != "english" else "Which crop? rice, sugarcane, cotton, groundnut"), {}

    # ─── Step 3: Days ─────────
    if farmer.get("days_after_sowing") is None:
        days = _extract_days(user_text)
        if days is not None:
            updates["days_after_sowing"] = days
            updates["onboarding_complete"] = True
            crop = farmer.get("primary_crop")
            district = farmer.get("district")
            return (f"அருமை! {district} - {crop}, {days} நாள். கேள்வி கேளுங்கள்!"
                    if lang != "english" else f"Done! {crop} in {district}, {days} days. Ask me anything!"), updates
        else:
            return ("நடவு எத்தனை நாள்? உதாரணம்: 20, 30, 60"
                    if lang != "english" else "Days since sowing? Example: 20, 30, 60"), {}

    updates["onboarding_complete"] = True
    return "கேள்வி கேளுங்கள்!", updates


def _extract_crop(text: str) -> str | None:
    text_clean = re.sub(r"[.,!?]", "", text.lower().strip())
    # Longest match first
    for kw, crop in sorted(CROP_MAP.items(), key=lambda x: -len(x[0])):
        if kw.lower() in text_clean:
            return crop
    for word in text_clean.split():
        if word in CROP_MAP:
            return CROP_MAP[word]
    return None


def _extract_days(text: str) -> int | None:
    num = _text_to_number(text)
    text_lower = text.lower()
    
    multiplier = 1
    if any(w in text_lower for w in ["மாதம்", "மாதங்கள்", "மாசம்", "month", "months"]):
        multiplier = 30
    elif any(w in text_lower for w in ["வாரம்", "வாரங்கள்", "week", "weeks"]):
        multiplier = 7
        
    if num is not None:
        result = num * multiplier
        if 0 <= result <= 365:
            return result
        return None
        
    if "நேற்று" in text_lower or "yesterday" in text_lower:
        return 1
    if multiplier > 1:
        return multiplier
    return None
