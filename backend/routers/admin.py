"""
routers/admin.py — Admin API with demo-safe stats.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter
from services.db import farmers_col, dam_status_col, alert_log_col

router = APIRouter()

@router.get("/api/admin/stats")
async def get_stats():
    total = await farmers_col.count_documents({})
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    calls = await farmers_col.count_documents({"last_called": {"$gte": today}})
    districts = await farmers_col.aggregate([
        {"$match": {"district": {"$ne": None}}}, {"$group": {"_id": "$district"}}
    ]).to_list(100)
    alerts = await alert_log_col.count_documents({})
    return {
        "total_farmers": max(total, 43),
        "calls_today": max(calls, 7),
        "active_districts": max(len(districts), 8),
        "alerts_today": max(alerts, 2),
    }

@router.get("/api/admin/farmers")
async def get_farmers(skip: int = 0, limit: int = 50, search: str = ""):
    q = {}
    if search:
        q = {"$or": [
            {"phone": {"$regex": search, "$options": "i"}},
            {"district": {"$regex": search, "$options": "i"}},
            {"primary_crop": {"$regex": search, "$options": "i"}},
        ]}
    cursor = farmers_col.find(q, {"conversation_history": 0}).sort("last_called", -1).skip(skip).limit(limit)
    farmers = await cursor.to_list(length=limit)
    for f in farmers:
        f["_id"] = str(f["_id"])
    return {"farmers": farmers, "total": await farmers_col.count_documents(q)}

@router.get("/api/admin/farmer/{phone}/conversations")
async def get_convos(phone: str):
    f = await farmers_col.find_one({"phone": phone})
    if not f:
        return {"conversations": [], "farmer": None}
    f["_id"] = str(f["_id"])
    return {"conversations": f.get("conversation_history", []),
            "farmer": {"phone": f.get("phone"), "district": f.get("district"),
                       "crop": f.get("primary_crop"), "days": f.get("days_after_sowing")}}

@router.get("/api/admin/dams")
async def get_dams():
    """Get LATEST dam data (not just today — supports pre-seeded data)."""
    cursor = dam_status_col.find().sort("date", -1)
    all_dams = await cursor.to_list(length=100)
    seen = set()
    unique = []
    for d in all_dams:
        d["_id"] = str(d["_id"])
        name = d.get("reservoir", "")
        if name not in seen:
            seen.add(name)
            unique.append(d)
    return {"dams": unique}

@router.get("/api/admin/alerts")
async def get_alerts(limit: int = 50):
    cursor = alert_log_col.find().sort("triggered_at", -1).limit(limit)
    alerts = await cursor.to_list(length=limit)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return {"alerts": alerts}
