"""
services/intent_service.py — Zero-cost keyword intent detection.
Handles Whisper misheard words and fuzzy Tamil variants.
"""

INTENT_KEYWORDS = {
    "irrigation": [
        "irrigat", "water", "pump", "flood", "moisture", "dry", "canal",
        "should i water", "watering", "bore", "borewell", "drip", "tanker",
        "தண்ணீர் விட", "நீர் விட",
        "பாசனம்", "நீர்", "கால்வாய்", "தண்ணீர்", "நீர்ப்பாசனம்",
        "போடணும", "தண்ணி", "ஈரம்", "வறட்சி",
        "thanni", "paasanam", "neer", "kalvaai",
    ],
    "disease": [
        "disease", "yellow", "spot", "leaf", "pest", "insect",
        "brown", "wilt", "rot", "fungus", "blight", "virus",
        "damage", "dying", "drying", "curl", "hole", "white", "orange",
        "நோய்", "பூச்சி", "இலை", "மஞ்சள்", "கருகல்", "அழுகல்",
        "பூஞ்சை", "புழு", "வாடல்", "புள்ளி", "சுருள்",
        "மஞ்சளா", "கருப்பு", "பழுப்பு", "ஆரஞ்சு", "நிறம்", "நிறத்தில்",
        "manjal", "ilai", "poochi", "noi", "spot",
    ],
    "fertilizer": [
        "fertilizer", "urea", "nutrient", "npk", "nitrogen",
        "phosphorus", "potassium", "deficien", "manure", "compost",
        "dap", "ssp", "mop", "dose",
        "உரம்", "தழை", "மணி", "யூரியா", "எரு",
        "பிரத்திலைஜர்", "uram",
    ],
    "crop_recommend": [
        "which crop", "what crop", "best crop", "suggest crop",
        "what to grow", "next crop", "what should i plant",
        "என்ன பயிர்", "எந்த பயிர்", "அடுத்த", "போடலாம்",
        "விதைக்கலாம்", "சாகுபடி", "என்ன நடவு", "அடுத்த முறை",
        "aduthu", "enna payir", "enna podalam", "next season",
    ],
    "dam": [
        "dam", "reservoir", "release", "storage",
        "mettur", "bhavanisagar", "amaravathi", "vaigai",
        "papanasam", "manimuthar",
        "அணை", "கால்வாய்", "நீர் திறப்பு", "நீர்த்தேக்கம்",
        "மேட்டூர்", "பவானிசாகர்", "அமராவதி", "வைகை",
        "பாப்பநாசம்", "மணிமுத்தாறு", "நீர் நிலை",
        "anai", "thirappu",
    ],
    "weather": [
        # Dedicated weather intent — separated from irrigation
        "weather", "rain", "temperature", "forecast", "climate",
        "மழை", "வானிலை", "வெப்பநிலை", "காற்று", "வெதர்",
        "நிலவரம்", "நிலை",  # "status" — commonly used for weather
        "rain tomorrow", "மழை வரும", "மழை பெய்யும",
        # Whisper misheard variants of வானிலை
        "மாணியில்", "பாணியிலேயே", "பாணி", "மாணி",
        "vaanilai", "mazhai", "weather",
    ],
    "yield": [
        "yield", "harvest", "income", "profit", "production",
        "விளைச்சல்", "எவ்வளவு", "மகசூல்", "லாபம்", "விலை",
        "vilaichal", "profit",
    ],
}


def detect_intents(text: str) -> list[str]:
    text_lower = text.lower()
    detected = []
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(intent)

    # "weather" intent should also trigger for irrigation context
    if "weather" in detected and "irrigation" not in detected:
        # Pure weather question — keep as weather
        pass

    # If irrigation + dam keywords, include both
    if "irrigation" in detected:
        dam_words = ["அணை", "dam", "canal", "கால்வாய்", "mettur", "vaigai"]
        if any(w in text_lower for w in dam_words) and "dam" not in detected:
            detected.append("dam")

    # Map "weather" to "general" with weather flag for pipeline
    if "weather" in detected and len(detected) == 1:
        return ["general"]  # Pipeline fetches weather for "general"

    if not detected:
        return ["general"]

    # Remove "weather" if other specific intents exist
    if "weather" in detected and len(detected) > 1:
        detected.remove("weather")

    return detected
