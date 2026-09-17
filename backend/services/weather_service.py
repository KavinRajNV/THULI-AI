"""
services/weather_service.py — Open-Meteo API Integration.
Completely replaces the paid WeatherAPI with free Open-Meteo.
Uses lat/lon provided by the farmer profile, falling back to district centroids.
"""
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import async_session
from models import WeatherCache
import data.loader

async def get_weather(district: str = None, lat: float = None, lon: float = None) -> dict:
    """Fetch weather by lat/lon using Open-Meteo. District is used for fallback centroid lookup."""
    
    # 1. Resolve coordinates
    if not lat or not lon:
        if not district:
            return {"error": "No coordinates or district provided"}
        
        CENTROIDS = data.loader.DISTRICT_CENTROIDS
        dl = district.lower().strip()
        found = False
        
        # Exact match first
        for key, coords in CENTROIDS.items():
            if key.lower().strip() == dl:
                lat, lon = coords["lat"], coords["lon"]
                found = True
                break
                
        # Partial match
        if not found:
            for key, coords in CENTROIDS.items():
                if dl in key.lower() or key.lower() in dl:
                    lat, lon = coords["lat"], coords["lon"]
                    found = True
                    break
                    
        if not found:
            return {"error": f"Could not resolve coordinates for district: {district}"}

    # Generate a cache key rounded to 2 decimal places (approx 1km accuracy) to group nearby requests
    cache_key = f"openmeteo_{round(lat, 2)}_{round(lon, 2)}"

    try:
        async with async_session() as session:
            result = await session.execute(select(WeatherCache).where(WeatherCache.cache_key == cache_key))
            cached = result.scalars().first()
            if cached and cached.cached_at:
                if datetime.utcnow() - cached.cached_at < timedelta(hours=6):
                    print(f"🌤️ Open-Meteo cache hit: {cache_key}")
                    return cached.data
    except Exception as e:
        print(f"⚠️ Cache: {e}")

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,rain_sum,precipitation_probability_max,relative_humidity_2m_mean",
            "timezone": "auto",
            "forecast_days": 3
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            print(f"🌤️ Open-Meteo API: lat={lat} lon={lon}, status={resp.status_code}")
            resp.raise_for_status()
            raw = resp.json()

        daily = raw.get("daily", {})
        times = daily.get("time", [])
        
        result = {}
        labels = ["today", "tomorrow", "day3"]
        
        for i, label in enumerate(labels):
            if i < len(times):
                max_temp = daily.get("temperature_2m_max", [])[i]
                min_temp = daily.get("temperature_2m_min", [])[i]
                rain_sum = daily.get("rain_sum", [])[i]
                rain_prob = daily.get("precipitation_probability_max", [])[i]
                humidity = daily.get("relative_humidity_2m_mean", [])[i]
                
                # Determine KISAN.AI Irrigation Advice for today
                advice = ""
                if i == 0:
                    if rain_sum >= 5:
                        advice = "(Advice: Do not irrigate today. Rainfall is sufficient.)"
                    elif max_temp >= 35 and rain_sum < 2:
                        advice = "(Advice: Irrigation may be required. Temperature is high and rainfall is low.)"
                    else:
                        advice = "(Advice: Irrigation can be considered based on soil moisture.)"
                
                # Format to match what ai_service.py expects
                result[label] = {
                    "temp_c": max_temp,
                    "min_temp_c": min_temp,
                    "humidity": humidity,
                    "rainfall_mm": rain_sum,
                    "chance_of_rain": rain_prob if rain_prob is not None else 0,
                    "condition": advice, # Using condition field to pass the irrigation advice to the LLM
                }
                
        try:
            async with async_session() as session:
                stmt = pg_insert(WeatherCache).values(
                    cache_key=cache_key,
                    data=result,
                    cached_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=['cache_key'],
                    set_={'data': result, 'cached_at': datetime.utcnow()}
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            print(f"⚠️ Cache write error: {e}")
        
        print(f"✅ Open-Meteo Weather: rain={result.get('today',{}).get('rainfall_mm')}mm")
        return result
        
    except Exception as e:
        print(f"❌ Open-Meteo Weather: {e}")
        return {"error": str(e)}
