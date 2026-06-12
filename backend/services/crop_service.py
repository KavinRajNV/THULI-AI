"""
services/crop_service.py — Crop recommendation with model crash fallback.
If RandomForest fails (version mismatch), uses rule-based recommendation.
"""
import data.loader

# Rule-based fallback when ML model crashes
CROP_RULES = {
    # (soil_type, season) → crops
    # Based on TN agricultural practices
    "low_N": ["blackgram", "greengram", "groundnut"],  # legumes fix nitrogen
    "high_rainfall": ["rice", "sugarcane"],
    "low_rainfall": ["pearl millet", "sorghum", "groundnut"],
    "neutral_pH": ["rice", "maize", "cotton"],
    "acidic_pH": ["rice", "groundnut"],
    "alkaline_pH": ["cotton", "sorghum", "pearl millet"],
}

TN_DISTRICT_CROPS = {
    "thanjavur": ["rice", "blackgram", "sesame"],
    "ramanathapuram": ["rice", "pearl millet", "groundnut", "cotton"],
    "madurai": ["rice", "cotton", "groundnut"],
    "krishnagiri": ["mango", "tomato", "groundnut", "maize"],
    "dharmapuri": ["maize", "groundnut", "tomato"],
    "coimbatore": ["cotton", "maize", "coconut"],
    "erode": ["turmeric", "sugarcane", "cotton"],
    "tirunelveli": ["rice", "banana", "chilli"],
    "salem": ["maize", "groundnut", "tomato"],
    "vellore": ["rice", "groundnut", "sugarcane"],
}


def recommend_crop(district, weather=None):
    """Try ML model first, fall back to rules if it crashes."""
    # Try ML model
    if data.loader.CROP_MODEL is not None:
        try:
            result = _ml_recommend(district, weather)
            if result and "Error" not in result:
                return result
        except Exception as e:
            print(f"⚠️ ML model crashed: {e}")
            print("   Falling back to rule-based recommendation")

    # Rule-based fallback
    return _rule_based_recommend(district, weather)


def _ml_recommend(district, weather):
    """Use RandomForest.pkl."""
    from services.soil_service import get_soil_data
    soil = get_soil_data(district)
    temp, humidity, rainfall = 28.0, 65.0, 100.0
    if weather and isinstance(weather, dict) and "error" not in weather:
        t = weather.get("today", {})
        temp = t.get("temp_c", 28) or 28
        humidity = t.get("humidity", 65) or 65
        rainfall = t.get("rainfall_mm", 100) or 100
    features = [soil.get("N", 50), soil.get("P", 50), soil.get("K", 50),
                temp, humidity, soil.get("pH", 6.5), rainfall]
    ranges = [(0, 140), (5, 145), (5, 205), (8, 44), (14, 100), (3.5, 9.9), (20, 298)]
    clamped = [max(lo, min(hi, float(v) if v else (lo + hi) / 2)) for v, (lo, hi) in zip(features, ranges)]
    pred = data.loader.CROP_MODEL.predict([clamped])
    print(f"🌾 ML prediction: {pred[0]}")
    return str(pred[0])


def _rule_based_recommend(district, weather):
    """Rule-based crop recommendation when ML model unavailable."""
    from services.soil_service import get_soil_data
    soil = get_soil_data(district)
    dl = district.lower().strip() if district else ""

    # District-specific recommendations
    if dl in TN_DISTRICT_CROPS:
        crops = TN_DISTRICT_CROPS[dl]
        reason = f"Based on {district} region suitability"
    else:
        # Soil-based logic
        crops = []
        n = soil.get("N", 200)
        ph = soil.get("pH", 7.0)
        rainfall = 100
        if weather and isinstance(weather, dict) and "error" not in weather:
            rainfall = weather.get("today", {}).get("rainfall_mm", 100) or 100

        if n and n < 280:
            crops.extend(CROP_RULES["low_N"])
        if rainfall > 80:
            crops.extend(CROP_RULES["high_rainfall"])
        else:
            crops.extend(CROP_RULES["low_rainfall"])
        if ph and ph < 6.0:
            crops.extend(CROP_RULES["acidic_pH"])
        elif ph and ph > 7.5:
            crops.extend(CROP_RULES["alkaline_pH"])
        else:
            crops.extend(CROP_RULES["neutral_pH"])
        # Deduplicate
        crops = list(dict.fromkeys(crops))
        reason = f"Based on soil (N={n}, pH={ph}) and rainfall patterns"

    if not crops:
        crops = ["rice", "groundnut", "pearl millet"]
        reason = "General TN recommendation"

    result = f"{', '.join(crops[:3])} — {reason}"
    print(f"🌾 Rule-based: {result}")
    return result


def get_crop_stage(crop, days):
    cdf = data.loader.CROPDATA_DF
    if cdf.empty or not crop:
        return _est(days)
    cc = next((c for c in ["crop_ID", "crop_id", "Crop"] if c in cdf.columns), None)
    mc = next((c for c in ["MOI", "moi", "Days"] if c in cdf.columns), None)
    sc = next((c for c in ["Seedling_Stage", "Stage"] if c in cdf.columns), None)
    if not all([cc, mc, sc]):
        return _est(days)
    f = cdf[cdf[cc].str.lower().str.contains(crop.lower(), na=False)]
    if f.empty:
        return _est(days)
    try:
        f = f.copy()
        f["_d"] = abs(f[mc].astype(float) - days)
        return str(f.sort_values("_d").iloc[0][sc])
    except:
        return _est(days)


def _est(d):
    if d is None: return "Unknown"
    if d <= 15: return "Germination"
    if d <= 45: return "Vegetative"
    if d <= 90: return "Flowering"
    return "Harvest"


def get_irrigation_need(crop, days, district):
    stage = get_crop_stage(crop, days)
    idf = data.loader.IRRIGATION_DF
    if idf.empty:
        return f"Stage: {stage}. Irrigation data unavailable."
    cc = next((c for c in ["Crop_Type", "crop_type"] if c in idf.columns), None)
    sc = next((c for c in ["Crop_Growth_Stage", "growth_stage"] if c in idf.columns), None)
    nc = next((c for c in ["Irrigation_Need", "irrigation_need"] if c in idf.columns), None)
    if not all([cc, sc, nc]):
        return f"Stage: {stage}."
    f = idf[idf[cc].str.lower().str.contains(crop.lower(), na=False)]
    if not f.empty:
        sf = f[f[sc].str.lower().str.contains(stage.lower(), na=False)]
        if not sf.empty:
            f = sf
    if f.empty:
        return f"Stage: {stage}. No irrigation data for {crop}."
    try:
        need = f[nc].mode().iloc[0]
        return f"Stage: {stage}. Irrigation need: {need}"
    except:
        return f"Stage: {stage}."
