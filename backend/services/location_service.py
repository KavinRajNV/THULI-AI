"""
services/location_service.py — Robust Pincode/village → location data.
Integrates Thuli-AI pincode logic.
"""
import re
import requests
import time
import data.loader

PIN_API = "https://api.pincodeapi.in/api/v1/pincode"
NOMINATIM_SEARCH_API = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_API = "https://nominatim.openstreetmap.org/reverse"

def api_get(url, params=None):
    try:
        response = requests.get(
            url,
            params=params,
            timeout=10,
            headers={"User-Agent": "THULI-AI/1.0"}
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None

def clean(value, default="Not available"):
    if value is None:
        return default
    value = str(value).strip()
    if not value:
        return default
    return value

def get_village(address, default="Not available"):
    return clean(
        address.get("village") or address.get("town") or 
        address.get("municipality") or address.get("city") or 
        address.get("suburb") or address.get("hamlet"),
        default
    )

def get_district(address, default="Not available"):
    return clean(address.get("state_district") or address.get("district"), default)

def reverse_geocode(latitude, longitude):
    if latitude in [None, ""] or longitude in [None, ""]:
        return {}
    params = {
        "lat": latitude, "lon": longitude,
        "format": "json", "addressdetails": 1, "zoom": 18
    }
    data = api_get(NOMINATIM_REVERSE_API, params=params)
    return data if data else {}

def search_village(village, pincode, district, state):
    queries = [
        f"{village}, {pincode}, India",
        f"{village}, {district}, {state}, India",
        f"{village}, {state}, India"
    ]
    village_lower = village.lower().strip()
    
    for query in queries:
        params = {
            "q": query, "format": "json", 
            "addressdetails": 1, "limit": 10
        }
        data = api_get(NOMINATIM_SEARCH_API, params=params)
        if data:
            for place in data:
                address = place.get("address", {})
                display_name = place.get("display_name", "").lower()
                result_postcode = clean(address.get("postcode"), "")
                
                if result_postcode == pincode: return place
                if village_lower in display_name and pincode in display_name: return place
                if village_lower in display_name: return place
        time.sleep(1) # Respect Nominatim
    return None

def resolve_location(pincode=None, village_name=None) -> dict:
    """
    Returns structured dict:
    {
       "pincode": str, "village": str, "district": str, 
       "taluk": str, "block": str, "state": str, 
       "lat": float, "lon": float, "location": str
    }
    Returns {} if not found.
    """
    result = {}
    
    # Needs at least a pincode (since village_name alone is too ambiguous without district in this logic)
    # The original script relies on PIN logic as base
    if not pincode:
        # Fallback to centroid logic if no pincode but village is known (from original codebase)
        CENTROIDS = data.loader.DISTRICT_CENTROIDS
        if village_name and CENTROIDS:
            dl = village_name.lower().strip()
            for key, coords in CENTROIDS.items():
                if dl in key.lower() or key.lower() in dl:
                    return {"district": key, "lat": coords["lat"], "lon": coords["lon"]}
        return result

    # 1. Check PIN API
    pin_data = api_get(f"{PIN_API}/{pincode}")
    if not pin_data or not pin_data.get("success"):
        return result
        
    offices = pin_data.get("data", {}).get("post_offices", [])
    if not offices:
        return result
        
    pin_district = clean(offices[0].get("district"))
    pin_state = clean(offices[0].get("state"))
    
    # 2. If Village provided, try to search it
    found = None
    if village_name:
        found = search_village(village_name, pincode, pin_district, pin_state)
        
    # 3. Compile final result
    if found:
        address = found.get("address", {})
        result = {
            "pincode": pincode,
            "village": get_village(address, village_name),
            "district": get_district(address, pin_district),
            "taluk": clean(address.get("subdistrict") or address.get("taluk")),
            "block": clean(address.get("block")),
            "state": clean(address.get("state"), pin_state),
            "lat": found.get("lat"),
            "lon": found.get("lon"),
            "location": found.get("display_name")
        }
    else:
        # PIN-only mode (or village search failed). 
        # Return FIRST post office to avoid latency loop!
        office = offices[0]
        lat = office.get("latitude")
        lon = office.get("longitude")
        
        reverse_data = reverse_geocode(lat, lon)
        address = reverse_data.get("address", {})
        office_name = clean(office.get("office_name"))
        
        result = {
            "pincode": pincode,
            "village": get_village(address, office_name),
            "district": get_district(address, clean(office.get("district"))),
            "taluk": clean(address.get("subdistrict") or address.get("taluk")),
            "block": clean(address.get("block")),
            "state": clean(address.get("state"), clean(office.get("state"))),
            "lat": lat,
            "lon": lon,
            "location": clean(reverse_data.get("display_name"))
        }
        
    return result

def extract_pincode(text):
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else None

def extract_district_name(text):
    for d in data.loader.DISTRICT_CENTROIDS:
        if d.lower() in text.lower(): return d
    return None
