"""
services/weather_service.py — WeatherAPI using DISTRICT NAME (not lat/lon).
"""
import os
from datetime import datetime, timedelta
import httpx
from services.db import weather_cache_col

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
if not WEATHER_API_KEY or WEATHER_API_KEY == "your_weatherapi_key_here":
    print("❌ WEATHER_API_KEY not set!")
else:
    print(f"✅ WeatherAPI key loaded ({WEATHER_API_KEY[:6]}...)")

async def get_weather(district: str = None, lat: float = None, lon: float = None) -> dict:
    """Fetch weather by district name OR lat/lon. District name is preferred."""
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_weatherapi_key_here":
        return {"error": "WEATHER_API_KEY not set in .env"}

    # Build query — prefer district name (always works, no lat/lon needed)
    if district:
        query = f"{district},Tamil Nadu,India"
    elif lat and lon:
        query = f"{lat},{lon}"
    else:
        return {"error": "No district or coordinates"}

    cache_key = query.replace(" ", "_").lower()[:50]

    try:
        cached = await weather_cache_col.find_one({"_id": cache_key})
        if cached and cached.get("cached_at"):
            if datetime.utcnow() - cached["cached_at"] < timedelta(hours=6):
                print(f"🌤️ Weather cache hit: {cache_key}")
                return cached.get("data", {})
    except Exception as e:
        print(f"⚠️ Cache: {e}")

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "http://api.weatherapi.com/v1/forecast.json",
                params={"key": WEATHER_API_KEY, "q": query, "days": 3},
            )
            print(f"🌤️ Weather API: q={query}, status={resp.status_code}")
            resp.raise_for_status()
            raw = resp.json()

        forecast = raw.get("forecast", {}).get("forecastday", [])
        result = {}
        for i, label in enumerate(["today", "tomorrow", "day3"]):
            if i < len(forecast):
                day = forecast[i]["day"]
                result[label] = {
                    "temp_c": day.get("avgtemp_c"),
                    "humidity": day.get("avghumidity"),
                    "rainfall_mm": day.get("totalprecip_mm", 0),
                    "chance_of_rain": day.get("daily_chance_of_rain", 0),
                    "condition": day.get("condition", {}).get("text", ""),
                }
        try:
            await weather_cache_col.update_one(
                {"_id": cache_key}, {"$set": {"data": result, "cached_at": datetime.utcnow()}}, upsert=True)
        except: pass
        print(f"✅ Weather: {result.get('today',{}).get('condition')}, rain={result.get('today',{}).get('rainfall_mm')}mm")
        return result
    except Exception as e:
        print(f"❌ Weather: {e}")
        return {"error": str(e)}
