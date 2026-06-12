"""
services/location_service.py — Pincode/village → district.
FIXED: uses data.loader module reference.
"""
import difflib, re
import httpx
import data.loader


def resolve_location(pincode=None, village_name=None):
    result = {}
    VILLAGES_DF = data.loader.VILLAGES_DF
    CENTROIDS = data.loader.DISTRICT_CENTROIDS

    if pincode and not VILLAGES_DF.empty:
        pin_col = _fc(VILLAGES_DF, ["Pincode","pincode","PIN"])
        if pin_col:
            matches = VILLAGES_DF[VILLAGES_DF[pin_col].astype(str).str.strip() == str(pincode).strip()]
            if not matches.empty:
                row = matches.iloc[0]
                dc = _fc(VILLAGES_DF, ["District","district"]); vc = _fc(VILLAGES_DF, ["Village Name","Village"])
                if dc: result["district"] = str(row[dc]).strip().title()
                if vc: result["village"] = str(row[vc]).strip().title()

    if not result.get("district") and village_name and not VILLAGES_DF.empty:
        vc = _fc(VILLAGES_DF, ["Village Name","Village"]); dc = _fc(VILLAGES_DF, ["District","district"])
        if vc and dc:
            all_v = VILLAGES_DF[vc].dropna().astype(str).str.strip().str.lower().tolist()
            close = difflib.get_close_matches(village_name.lower().strip(), all_v, n=1, cutoff=0.6)
            if close:
                mr = VILLAGES_DF[VILLAGES_DF[vc].str.strip().str.lower() == close[0]].iloc[0]
                result["district"] = str(mr[dc]).strip().title()
                result["village"] = str(mr[vc]).strip().title()

    if not result.get("district") and pincode:
        try:
            resp = httpx.get(f"https://api.postalpincode.in/pincode/{pincode}", timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                if d and d[0].get("Status") == "Success":
                    po = d[0]["PostOffice"][0]
                    result["district"] = po.get("District","").title()
                    result["village"] = po.get("Name","").title()
        except: pass

    # Add lat/lon from centroids
    district = result.get("district", "")
    if district and CENTROIDS:
        dl = district.lower().strip()
        for key, coords in CENTROIDS.items():
            if key.lower().strip() == dl:
                result["lat"] = coords["lat"]; result["lon"] = coords["lon"]
                result["district"] = key; break
        else:
            for key, coords in CENTROIDS.items():
                if dl in key.lower() or key.lower() in dl:
                    result["lat"] = coords["lat"]; result["lon"] = coords["lon"]
                    result["district"] = key; break
    return result


def extract_pincode(text):
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else None

def extract_district_name(text):
    for d in data.loader.DISTRICT_CENTROIDS:
        if d.lower() in text.lower(): return d
    return None

def _fc(df, c): return next((x for x in c if x in df.columns), None)
