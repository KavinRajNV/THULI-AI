"""
data/loader.py — Load all datasets into memory at startup.
Global DataFrames / dicts accessed by services.
"""

import json
import os
import pickle

import pandas as pd

# ─── Find the dataset directory automatically ─────────────────────────
# Your CSVs could be in any of these locations depending on how you set up.
# We check all of them, pick the one that actually has CSV files.

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_candidates = [
    os.path.join(_backend_dir, "datasets"),                          # backend/datasets/
    os.path.join(_backend_dir, "Dataset"),                           # backend/Dataset/
    os.path.join(_backend_dir, "dataset"),                           # backend/dataset/
    os.path.join(_backend_dir, "Datasets"),                          # backend/Datasets/
    os.path.join(_backend_dir, "..", "Dataset"),                     # ../Dataset/
    os.path.join(_backend_dir, "..", "Dataset", "Datasets"),         # ../Dataset/Datasets/
    os.path.join(_backend_dir, "..", "datasets"),                    # ../datasets/
]


def _find_dataset_dir():
    """Find the directory that actually contains CSV files."""
    for p in _candidates:
        abs_p = os.path.abspath(p)
        if os.path.isdir(abs_p):
            csv_files = [f for f in os.listdir(abs_p) if f.endswith((".csv", ".pkl", ".json", ".xlsx"))]
            if len(csv_files) >= 3:  # At least a few data files
                print(f"📂 Dataset directory found: {abs_p} ({len(csv_files)} data files)")
                return abs_p
    # Fallback
    fallback = os.path.abspath(_candidates[0])
    print(f"⚠️  No dataset directory found! Looked in:")
    for p in _candidates:
        print(f"     {os.path.abspath(p)} — {'EXISTS' if os.path.isdir(p) else 'NOT FOUND'}")
    return fallback


BASE = _find_dataset_dir()

# ─── Global DataFrames ───────────────────────────────────────────────
VILLAGES_DF: pd.DataFrame = pd.DataFrame()
SOIL_DF: pd.DataFrame = pd.DataFrame()
KRISHNAGIRI_DF: pd.DataFrame = pd.DataFrame()
THANJAVUR_DF: pd.DataFrame = pd.DataFrame()
DHARMAPURI_DF: pd.DataFrame = pd.DataFrame()
CROPDATA_DF: pd.DataFrame = pd.DataFrame()
IRRIGATION_DF: pd.DataFrame = pd.DataFrame()
YIELD_DF: pd.DataFrame = pd.DataFrame()
DISEASE_DF: pd.DataFrame = pd.DataFrame()
CROP_REC_DF: pd.DataFrame = pd.DataFrame()
RESERVOIR_DF: pd.DataFrame = pd.DataFrame()

# ─── Global dicts / models ───────────────────────────────────────────
DAM_IRRIGATION_DATA: dict = {}
DISTRICT_CENTROIDS: dict = {}
CROP_MODEL = None  # RandomForest.pkl


def _safe_read_csv(path: str, **kwargs) -> pd.DataFrame:
    """Read CSV with error handling. Tries underscore/space variants."""
    try:
        if os.path.exists(path):
            return pd.read_csv(path, **kwargs)
        # Try alternate name (space ↔ underscore)
        basename = os.path.basename(path)
        dirname = os.path.dirname(path)
        if "_" in basename:
            alt = os.path.join(dirname, basename.replace("_", " "))
        else:
            alt = os.path.join(dirname, basename.replace(" ", "_"))
        if os.path.exists(alt):
            return pd.read_csv(alt, **kwargs)
        # Try case-insensitive match
        if os.path.isdir(dirname):
            for f in os.listdir(dirname):
                if f.lower() == basename.lower():
                    return pd.read_csv(os.path.join(dirname, f), **kwargs)
        print(f"⚠️  File not found: {path}")
    except Exception as e:
        print(f"⚠️  Error loading {path}: {e}")
    return pd.DataFrame()


def _find_file(base_dir: str, *names) -> str:
    """Find the first existing file from a list of candidate names."""
    for name in names:
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            return path
    # Case-insensitive fallback
    if os.path.isdir(base_dir):
        dir_files = os.listdir(base_dir)
        for name in names:
            target = os.path.basename(name).lower()
            for f in dir_files:
                if f.lower() == target:
                    return os.path.join(base_dir, f)
    return os.path.join(base_dir, names[0])


def load_all_datasets():
    """Load every dataset into global variables. Called once at startup."""
    global VILLAGES_DF, SOIL_DF, KRISHNAGIRI_DF, THANJAVUR_DF, DHARMAPURI_DF
    global CROPDATA_DF, IRRIGATION_DF, YIELD_DF, DISEASE_DF, CROP_REC_DF
    global RESERVOIR_DF, DAM_IRRIGATION_DATA, DISTRICT_CENTROIDS, CROP_MODEL

    print(f"📂 Loading datasets from: {BASE}")

    # Villages (pincode/district resolver)
    VILLAGES_DF = _safe_read_csv(os.path.join(BASE, "Villages.csv"))
    if not VILLAGES_DF.empty:
        VILLAGES_DF.columns = [c.strip() for c in VILLAGES_DF.columns]
        print(f"   ✅ Villages: {len(VILLAGES_DF)} rows")

    # Generic soil data (all districts) — handles "Soil data.csv" and "Soil_data.csv"
    SOIL_DF = _safe_read_csv(_find_file(BASE, "Soil_data.csv", "Soil data.csv"))
    if not SOIL_DF.empty:
        SOIL_DF.columns = [c.strip() for c in SOIL_DF.columns]
        print(f"   ✅ Soil_data: {len(SOIL_DF)} rows")

    # District-specific soil files
    KRISHNAGIRI_DF = _safe_read_csv(os.path.join(BASE, "KrishnaGiri.csv"))
    if not KRISHNAGIRI_DF.empty:
        KRISHNAGIRI_DF.columns = [c.strip() for c in KRISHNAGIRI_DF.columns]
        print(f"   ✅ KrishnaGiri: {len(KRISHNAGIRI_DF)} rows")

    # Dharmapuri — skip first 2 garbage header rows
    DHARMAPURI_DF = _safe_read_csv(os.path.join(BASE, "Dharmapuri.csv"), skiprows=2)
    if not DHARMAPURI_DF.empty:
        expected_cols = ["Sample", "pH", "EC", "OC", "N", "P", "K",
                         "Sand", "Silt", "Clay", "TexturalClass", "District"]
        if len(DHARMAPURI_DF.columns) == len(expected_cols):
            DHARMAPURI_DF.columns = expected_cols
        print(f"   ✅ Dharmapuri: {len(DHARMAPURI_DF)} rows")

    # Thanjavur (Excel) — handles "Thanjvur dataset.xlsx" and "Thanjvur_dataset.xlsx"
    try:
        xlsx_path = _find_file(BASE, "Thanjvur_dataset.xlsx", "Thanjvur dataset.xlsx")
        if os.path.exists(xlsx_path):
            THANJAVUR_DF = pd.read_excel(xlsx_path)
            THANJAVUR_DF.columns = [c.strip() for c in THANJAVUR_DF.columns]
            print(f"   ✅ Thanjavur: {len(THANJAVUR_DF)} rows")
    except Exception as e:
        print(f"⚠️  Thanjavur load error: {e}")

    # Crop data (stage tracking)
    CROPDATA_DF = _safe_read_csv(os.path.join(BASE, "cropdata_updated.csv"))
    if not CROPDATA_DF.empty:
        print(f"   ✅ cropdata_updated: {len(CROPDATA_DF)} rows")

    # Irrigation prediction
    IRRIGATION_DF = _safe_read_csv(os.path.join(BASE, "irrigation_prediction.csv"))
    if not IRRIGATION_DF.empty:
        print(f"   ✅ irrigation_prediction: {len(IRRIGATION_DF)} rows")

    # Yield data
    YIELD_DF = _safe_read_csv(os.path.join(BASE, "Yield-data.csv"))
    if not YIELD_DF.empty:
        print(f"   ✅ Yield-data: {len(YIELD_DF)} rows")

    # Plant diseases
    DISEASE_DF = _safe_read_csv(os.path.join(BASE, "plant_disease.csv"))
    if not DISEASE_DF.empty:
        print(f"   ✅ plant_disease: {len(DISEASE_DF)} rows")

    # Crop recommendation reference
    CROP_REC_DF = _safe_read_csv(os.path.join(BASE, "Crop_recommendation.csv"))
    if not CROP_REC_DF.empty:
        print(f"   ✅ Crop_recommendation: {len(CROP_REC_DF)} rows")

    # Reservoir 10-year history
    RESERVOIR_DF = _safe_read_csv(os.path.join(BASE, "tn_reservoir_10years_19dams.csv"))
    if not RESERVOIR_DF.empty:
        if "date" in RESERVOIR_DF.columns:
            RESERVOIR_DF["date"] = pd.to_datetime(RESERVOIR_DF["date"], errors="coerce")
        print(f"   ✅ tn_reservoir_10years_19dams: {len(RESERVOIR_DF)} rows")

    # Dam irrigation dataset (JSON)
    try:
        json_path = _find_file(BASE, "tn_dam_irrigation_dataset.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                DAM_IRRIGATION_DATA = json.load(f)
            print(f"   ✅ tn_dam_irrigation_dataset: loaded")
    except Exception as e:
        print(f"⚠️  Dam JSON load error: {e}")

    # District centroids (in data/ folder, not datasets)
    try:
        centroid_path = os.path.join(os.path.dirname(__file__), "district_centroids.json")
        if os.path.exists(centroid_path):
            with open(centroid_path, "r", encoding="utf-8") as f:
                DISTRICT_CENTROIDS = json.load(f)
            print(f"   ✅ district_centroids: {len(DISTRICT_CENTROIDS)} districts")
    except Exception as e:
        print(f"⚠️  Centroid load error: {e}")

    # RandomForest model — might be in models/ subfolder or at root
    try:
        model_path = _find_file(BASE,
            "RandomForest.pkl",
            os.path.join("models", "RandomForest.pkl"),
        )
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                CROP_MODEL = pickle.load(f)
            print(f"   ✅ RandomForest.pkl: loaded")
    except Exception as e:
        print(f"⚠️  Model load error: {e}")

    print("✅ Dataset loading complete.")