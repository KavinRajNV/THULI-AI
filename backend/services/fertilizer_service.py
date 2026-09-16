"""
services/fertilizer_service.py — Rule-based fertilizer recommendation.
NO ML model. Pure rules from NPK deficiency thresholds.
"""

from services.soil_service import get_soil_data

# Thresholds (kg/ha)
# N < 280 = low, 280-560 = medium, >560 = high
# P < 10 = low, 10-25 = medium, >25 = high
# K < 108 = low, 108-280 = medium, >280 = high

FERTILIZER_RULES = {
    "N_low": {
        "fertilizer": "Urea",
        "dose": "50 kg/acre",
        "timing": "Split: 50% basal + 50% top dress at 30 days",
        "explanation": "Nitrogen is low. Urea provides quick N boost for vegetative growth.",
    },
    "N_medium": {
        "fertilizer": "Urea",
        "dose": "25 kg/acre",
        "timing": "Top dress only at 25-30 days after sowing",
        "explanation": "Nitrogen is moderate. Light top dressing is sufficient.",
    },
    "P_low": {
        "fertilizer": "Single Super Phosphate (SSP)",
        "dose": "50 kg/acre",
        "timing": "Basal application before sowing",
        "explanation": "Phosphorus is low. SSP should be applied at sowing for root development.",
    },
    "P_medium": {
        "fertilizer": "DAP (Di-Ammonium Phosphate)",
        "dose": "25 kg/acre",
        "timing": "Basal application",
        "explanation": "Phosphorus is moderate. DAP gives both N and P.",
    },
    "K_low": {
        "fertilizer": "Muriate of Potash (MOP)",
        "dose": "25 kg/acre",
        "timing": "Basal application",
        "explanation": "Potassium is low. MOP helps disease resistance and grain quality.",
    },
    "K_medium": {
        "fertilizer": "Muriate of Potash (MOP)",
        "dose": "15 kg/acre",
        "timing": "Basal application",
        "explanation": "Potassium is moderate. Light application recommended.",
    },
    "balanced": {
        "fertilizer": "NPK Complex 17:17:17",
        "dose": "25 kg/acre",
        "timing": "Basal application",
        "explanation": "Soil nutrients are balanced. A general-purpose complex is sufficient.",
    },
}


def _classify_nutrient(value: float | None, thresholds: tuple) -> str:
    """Classify a nutrient value as low/medium/high."""
    if value is None:
        return "unknown"
    low, high = thresholds
    if value < low:
        return "low"
    elif value <= high:
        return "medium"
    return "high"


def get_recommendation(district: str, crop: str = None, days: int = None) -> dict:
    """
    1. Get soil NPK for district
    2. Classify each as low/medium/high
    3. Return the primary deficiency + recommendation

    Returns: {primary_deficiency, fertilizer, dose, timing, explanation, soil_levels}
    """
    soil = get_soil_data(district)

    n_level = _classify_nutrient(soil.get("N"), (280, 560))
    p_level = _classify_nutrient(soil.get("P"), (10, 25))
    k_level = _classify_nutrient(soil.get("K"), (108, 280))

    # Determine primary deficiency (priority: N > P > K)
    recommendations = []

    if n_level == "low":
        recommendations.append(("N_low", "Nitrogen (N) — Low"))
    elif n_level == "medium":
        recommendations.append(("N_medium", "Nitrogen (N) — Medium"))

    if p_level == "low":
        recommendations.append(("P_low", "Phosphorus (P) — Low"))
    elif p_level == "medium":
        recommendations.append(("P_medium", "Phosphorus (P) — Medium"))

    if k_level == "low":
        recommendations.append(("K_low", "Potassium (K) — Low"))
    elif k_level == "medium":
        recommendations.append(("K_medium", "Potassium (K) — Medium"))

    if not recommendations:
        rule = FERTILIZER_RULES["balanced"]
        return {
            "primary_deficiency": "None — balanced soil",
            "fertilizer": rule["fertilizer"],
            "dose": rule["dose"],
            "timing": rule["timing"],
            "explanation": rule["explanation"],
            "soil_levels": {"N": n_level, "P": p_level, "K": k_level},
            "soil_values": soil,
        }

    # Return the primary (most severe) deficiency
    primary_key, primary_label = recommendations[0]
    rule = FERTILIZER_RULES[primary_key]

    result = {
        "primary_deficiency": primary_label,
        "fertilizer": rule["fertilizer"],
        "dose": rule["dose"],
        "timing": rule["timing"],
        "explanation": rule["explanation"],
        "soil_levels": {"N": n_level, "P": p_level, "K": k_level},
        "soil_values": soil,
    }

    # Add secondary recommendation if multiple deficiencies
    if len(recommendations) > 1:
        sec_key, sec_label = recommendations[1]
        sec_rule = FERTILIZER_RULES[sec_key]
        result["secondary"] = {
            "deficiency": sec_label,
            "fertilizer": sec_rule["fertilizer"],
            "dose": sec_rule["dose"],
        }

    # Crop-specific note
    if crop:
        result["crop_note"] = _get_crop_note(crop)

    return _adjust_for_growth_stage(result, crop, days)


def _get_crop_note(crop: str) -> str:
    """Simple crop-specific fertilizer notes."""
    crop_lower = crop.lower()
    notes = {
        "rice": "For paddy: apply Zinc Sulphate 10 kg/acre as basal in zinc-deficient soils.",
        "paddy": "For paddy: apply Zinc Sulphate 10 kg/acre as basal in zinc-deficient soils.",
        "cotton": "Cotton benefits from Boron spray at flowering stage.",
        "sugarcane": "Sugarcane needs heavy N: split into 3 doses at 0, 45, and 90 days.",
        "groundnut": "Groundnut: apply Gypsum 200 kg/acre at pegging stage for pod filling.",
        "maize": "Maize: split N into 3 doses — basal, knee-high, and tasseling stage.",
    }
    for key, note in notes.items():
        if key in crop_lower:
            return note
    return ""


def _adjust_for_growth_stage(result: dict, crop: str, days: int | None) -> dict:
    if days is None or not crop:
        return result
        
    crop_l = crop.lower()
    
    # Real stage thresholds based on utils.py logic
    if crop_l in ["rice", "paddy", "maize", "wheat", "barley", "millets", "sorghum", "pearl millet"]: # Cereal-like
        basal_window = 15
        top_dress_window = 45 # tillering
        late_top_dress = 75 # panicle initiation
        maturity_window = 90
        
        if days <= basal_window:
            stage = "Germination/Seedling"
        elif days <= top_dress_window:
            stage = "Active Tillering"
        elif days <= late_top_dress:
            stage = "Panicle Initiation"
        else:
            stage = "Maturity"
            
    elif crop_l == "sugarcane":
        basal_window = 20
        top_dress_window = 60 # 45 DAS tillering
        late_top_dress = 150 # 90-120 DAS grand growth
        maturity_window = 250
        
        if days <= basal_window:
            stage = "Early Growth"
        elif days <= top_dress_window:
            stage = "Tillering"
        elif days <= late_top_dress:
            stage = "Grand Growth"
        else:
            stage = "Maturity"
            
    elif crop_l in ["groundnut", "blackgram", "greengram", "pulses", "sesame"]: # N-Fixers
        basal_window = 20
        top_dress_window = 40 # flowering/pegging
        late_top_dress = 40
        maturity_window = 70
        
        if days <= basal_window:
            stage = "Vegetative"
        elif days <= top_dress_window:
            stage = "Flowering/Pegging"
        else:
            stage = "Maturity"
            
    elif crop_l == "cotton":
        basal_window = 20
        top_dress_window = 60 # squaring
        late_top_dress = 100 # boll development
        maturity_window = 130
        
        if days <= basal_window:
            stage = "Vegetative"
        elif days <= top_dress_window:
            stage = "Squaring/Flowering"
        elif days <= late_top_dress:
            stage = "Boll Development"
        else:
            stage = "Maturity"
            
    else:
        # Generic fallback
        basal_window = 15
        top_dress_window = 45
        maturity_window = 90
        if days <= basal_window:
            stage = "Early Vegetative"
        elif days <= top_dress_window:
            stage = "Mid Vegetative"
        else:
            stage = "Maturity"

    # Now adjust timing/dose based on stage
    current_timing = result["timing"].lower()
    
    if stage == "Maturity" or stage == "Boll Development" or days > maturity_window:
        result["timing"] = f"Crop is at {stage} stage ({days} days). No further nutrient application is recommended at this late stage."
        result["dose"] = "0 kg"
        result["explanation"] += f" (Note: Skipped as crop is {days} days old)."
    elif days > basal_window:
        # Past basal window
        if "basal" in current_timing:
            if "split" in current_timing or "top dress" in current_timing:
                result["timing"] = f"Crop is at {stage} stage ({days} days), past the basal window. Apply ONLY the top-dress portion of the recommended dose now."
            else:
                result["timing"] = f"Crop is at {stage} stage ({days} days), past the ideal basal application window. Only apply as a light top-dress if severe deficiency is visible."
    else:
        # Within basal window
        result["timing"] = f"Crop is at {stage} stage ({days} days). {result['timing']}."

    return result
