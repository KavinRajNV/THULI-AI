"""
services/pipeline_service.py — Intent-driven data gathering.
Passes farmer_text to dam_service for direct name extraction.
"""
import asyncio
from services.intent_service import detect_intents
from services import weather_service, dam_service, soil_service, crop_service
from services import disease_service, fertilizer_service

async def build_context(farmer_text: str, farmer_profile: dict) -> dict:
    intents = detect_intents(farmer_text)
    context = {"intents": intents}
    district = farmer_profile.get("district")
    crop = farmer_profile.get("primary_crop")
    days = farmer_profile.get("days_after_sowing")
    lat = farmer_profile.get("lat")
    lon = farmer_profile.get("lon")
    tasks = {}

    if "irrigation" in intents:
        if district or (lat and lon): tasks["weather"] = weather_service.get_weather(district=district, lat=lat, lon=lon)
        # Pass farmer_text so dam_service can extract dam names
        tasks["dam"] = dam_service.get_dam_context(district=district, farmer_text=farmer_text)
        if district: tasks["soil"] = asyncio.to_thread(soil_service.get_soil_data, district)
        if crop and days is not None:
            tasks["irrigation_need"] = asyncio.to_thread(crop_service.get_irrigation_need, crop, days, district)
            tasks["crop_stage"] = asyncio.to_thread(crop_service.get_crop_stage, crop, days)

    elif "dam" in intents:
        tasks["dam"] = dam_service.get_dam_context(district=district, farmer_text=farmer_text)

    elif "disease" in intents:
        tasks["disease"] = asyncio.to_thread(disease_service.match_disease, farmer_text, crop)
        if district:
            tasks["soil"] = asyncio.to_thread(soil_service.get_soil_data, district)
            tasks["fertilizer"] = asyncio.to_thread(fertilizer_service.get_recommendation, district, crop)

    elif "fertilizer" in intents:
        if district:
            tasks["soil"] = asyncio.to_thread(soil_service.get_soil_data, district)
            tasks["fertilizer"] = asyncio.to_thread(fertilizer_service.get_recommendation, district, crop, days)

    elif "crop_recommend" in intents:
        if district:
            tasks["soil"] = asyncio.to_thread(soil_service.get_soil_data, district)
        if district or (lat and lon):
            tasks["weather"] = weather_service.get_weather(district=district, lat=lat, lon=lon)

    elif "location" in intents:
        from services import location_service
        from services.farmer_service import _text_to_pincode
        pincode = _text_to_pincode(farmer_text)
        if pincode:
            tasks["location_details"] = asyncio.to_thread(location_service.resolve_location, pincode)

    else:
        if district or (lat and lon): tasks["weather"] = weather_service.get_weather(district=district, lat=lat, lon=lon)

    from services import flag_service
    if district:
        tasks["regional_dictionary"] = flag_service.get_dictionary_for_district(district)

    if tasks:
        keys = list(tasks.keys())
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks.values(), return_exceptions=True), timeout=10.0)
            for k, v in zip(keys, results):
                if isinstance(v, Exception): print(f"  {k}: {v}")
                else: context[k] = v
        except asyncio.TimeoutError: print("Pipeline timeout")

    if "crop_recommend" in intents and district:
        try:
            context["crop_recommendation"] = await asyncio.wait_for(
                asyncio.to_thread(crop_service.recommend_crop, district, context.get("weather")), timeout=5.0)
        except Exception as e: print(f"  Crop rec: {e}")

    print(f"Pipeline: intents={intents}, data={[k for k in context if k!='intents']}")
    return context
