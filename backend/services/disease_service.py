"""
services/disease_service.py — Disease matching with Tamil→English translation.
FIXED: uses data.loader module reference.
"""
import re
import data.loader

SYMPTOM_TRANSLATIONS = {
    "மஞ்சள்": "yellow yellowing", "மஞ்சளா": "yellow yellowing", "மஞ்சல்": "yellow",
    "இலை": "leaf leaves", "கருகல்": "burn blight browning",
    "அழுகல்": "rot rotting decay", "புள்ளி": "spot spots",
    "வாடல்": "wilt wilting", "வாடி": "wilt", "பூச்சி": "pest insect",
    "புழு": "worm caterpillar larva", "பூஞ்சை": "fungus mold mildew",
    "வெள்ளை": "white powdery", "கருப்பு": "black dark",
    "பழுப்பு": "brown", "சிவப்பு": "red rust", "ஆரஞ்சு": "orange",
    "துரு": "rust", "உதிர்தல்": "falling shedding",
    "சுருள்": "curl curling", "காய்ந்து": "drying dried withered",
    "ஓட்டை": "hole borer", "நிறம்": "color discoloration",
    "நெல்": "rice paddy", "பருத்தி": "cotton",
    "கரும்பு": "sugarcane", "நிலக்கடலை": "groundnut",
    "மக்காச்சோளம்": "maize", "தக்காளி": "tomato",
}

def _translate(text):
    expanded = text.lower()
    for tamil, eng in SYMPTOM_TRANSLATIONS.items():
        if tamil in expanded:
            expanded += " " + eng
    return expanded

def match_disease(symptoms_text, crop=None):
    if data.loader.DISEASE_DF.empty:
        print("⚠️ Disease: dataset empty!")
        return []
    df = data.loader.DISEASE_DF.copy()
    expanded = _translate(symptoms_text)
    crop_eng = crop
    if crop:
        for t, e in SYMPTOM_TRANSLATIONS.items():
            if t in crop.lower():
                crop_eng = e.split()[0]; break
    if crop_eng:
        cc = _fc(df, ["Affected_Crop", "Crop"])
        if cc:
            cf = df[df[cc].str.lower().str.contains(crop_eng.lower(), na=False)]
            if not cf.empty: df = cf
    tokens = set(re.findall(r"\w+", expanded)) - {"the","is","a","an","and","or","in","of","my","it"}
    if not tokens: return []
    sc = _fc(df, ["Symptoms", "symptoms"]); dc = _fc(df, ["Diseases", "Disease"])
    tc = _fc(df, ["Treatment", "treatment"]); pc = _fc(df, ["Prevention", "prevention"])
    cc = _fc(df, ["Affected_Crop", "Crop"]); cac = _fc(df, ["Causes", "causes"])
    if not sc or not dc: return []
    scores = []
    for _, row in df.iterrows():
        combined = f"{str(row.get(sc,''))} {str(row.get(dc,''))} {str(row.get(cac,''))}".lower()
        overlap = len(tokens & set(re.findall(r"\w+", combined)))
        if overlap > 0:
            scores.append({"disease": row.get(dc), "crop": row.get(cc,"?") if cc else "?",
                "symptoms": row.get(sc,""), "treatment": row.get(tc,"") if tc else "",
                "prevention": row.get(pc,"") if pc else "", "score": overlap})
    scores.sort(key=lambda x: x["score"], reverse=True)
    print(f"🔬 Disease: {len(scores)} matches (top: {scores[0]['disease'] if scores else 'none'})")
    return scores[:2]

def _fc(df, c): return next((x for x in c if x in df.columns), None)
