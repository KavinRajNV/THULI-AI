"""
services/db.py — MongoDB Atlas connection (motor async driver).
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGODB_URI)
db = client.kisan_ai

# Collections
farmers_col = db.farmers
dam_status_col = db.dam_status
weather_cache_col = db.weather_cache
alert_log_col = db.alert_log
calls_col = db.calls
flags_col = db.flags
regional_dictionary_col = db.regional_dictionary


async def ensure_indexes():
    """Create indexes on first run."""
    await farmers_col.create_index("phone", unique=True)
    await dam_status_col.create_index([("date", 1), ("reservoir", 1)])
    await weather_cache_col.create_index("cached_at", expireAfterSeconds=21600)
    await alert_log_col.create_index("triggered_at")
    await calls_col.create_index("call_id", unique=True)
    await flags_col.create_index([("normalized_term", 1), ("district", 1)])
    await flags_col.create_index("status")
    await regional_dictionary_col.create_index([("district", 1), ("term", 1)], unique=True)
    print("✅ MongoDB indexes ensured.")
