"""
services/soil_service.py — Soil NPK/pH by district.
FIXED: uses data.loader.X (module reference) instead of direct import.
"""
import numpy as np
from services import loader  # Module reference — always gets current data after load_all_datasets()


def get_soil_data(district: str) -> dict:
    district_lower = district.lower().strip() if district else ""

    # District-specific files
    if "krishnagiri" in district_lower and not loader.KRISHNAGIRI_DF.empty:
        return _average_soil(loader.KRISHNAGIRI_DF)
    if "thanjavur" in district_lower and not loader.THANJAVUR_DF.empty:
        return _average_soil(loader.THANJAVUR_DF)
    if "dharmapuri" in district_lower and not loader.DHARMAPURI_DF.empty:
        return _average_soil(loader.DHARMAPURI_DF)

    # Generic fallback
    if not loader.SOIL_DF.empty:
        dist_col = _find_col(loader.SOIL_DF, ["District", "district"])
        if dist_col:
            filtered = loader.SOIL_DF[loader.SOIL_DF[dist_col].str.lower().str.strip() == district_lower]
            if not filtered.empty:
                print(f"🌱 Soil: found {len(filtered)} rows for {district}")
                return _average_soil(filtered)
        print(f"🌱 Soil: no match for {district}, using state average ({len(loader.SOIL_DF)} rows)")
        return _average_soil(loader.SOIL_DF)

    print("⚠️ Soil: no data loaded!")
    return _default_soil()


def _average_soil(df) -> dict:
    result = {}
    for cols, key in [
        (["N", "Nitrogen"], "N"), (["P", "Phosphorus"], "P"),
        (["K", "Potassium"], "K"), (["pH", "ph"], "pH"), (["OC", "Organic Carbon"], "OC"),
    ]:
        val = _safe_mean(df, cols)
        result[key] = round(val, 2) if val is not None else None
    tex_col = _find_col(df, ["TexturalClass", "Textural Class", "Texture"])
    result["texture"] = df[tex_col].mode().iloc[0] if tex_col and tex_col in df.columns else "Unknown"
    return result

def _safe_mean(df, candidates):
    for c in candidates:
        if c in df.columns:
            try:
                vals = df[c].dropna().astype(float)
                if len(vals) > 0: return float(np.mean(vals))
            except: continue
    return None

def _find_col(df, candidates):
    return next((c for c in candidates if c in df.columns), None)

def _default_soil():
    return {"N": 240.0, "P": 18.0, "K": 200.0, "pH": 7.2, "OC": 0.5, "texture": "Clay Loam"}
