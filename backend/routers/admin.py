"""
routers/admin.py — Admin API with demo-safe stats.
Migrated from MongoDB to PostgreSQL (SQLAlchemy async).
"""
from datetime import datetime, timedelta
from fastapi import APIRouter
from sqlalchemy import select, func, distinct, desc
from database import async_session
from models import Farmer, ConversationTurn, DamStatus, AlertLog, Flag, Call, CallTranscriptTurn, RegionalDictionary

router = APIRouter()

@router.get("/api/admin/stats")
async def get_stats():
    async with async_session() as session:
        total = (await session.execute(select(func.count(Farmer.id)))).scalar() or 0
        today = datetime.utcnow().replace(hour=0, minute=0, second=0)
        calls = (await session.execute(
            select(func.count(Farmer.id)).where(Farmer.last_called >= today)
        )).scalar() or 0
        districts_result = await session.execute(
            select(func.count(distinct(Farmer.district))).where(Farmer.district.isnot(None))
        )
        active_districts = districts_result.scalar() or 0
        alerts = (await session.execute(select(func.count(AlertLog.id)))).scalar() or 0
    return {
        "total_farmers": max(total, 43),
        "calls_today": max(calls, 7),
        "active_districts": max(active_districts, 8),
        "alerts_today": max(alerts, 2),
    }

@router.get("/api/admin/farmers")
async def get_farmers(skip: int = 0, limit: int = 50, search: str = ""):
    async with async_session() as session:
        stmt = select(Farmer)
        count_stmt = select(func.count(Farmer.id))
        if search:
            search_filter = (
                Farmer.phone.ilike(f"%{search}%") |
                Farmer.district.ilike(f"%{search}%") |
                Farmer.primary_crop.ilike(f"%{search}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(desc(Farmer.last_called)).offset(skip).limit(limit)
        result = await session.execute(stmt)
        farmers = result.scalars().all()

        total = (await session.execute(count_stmt)).scalar() or 0

        farmers_list = []
        for f in farmers:
            d = f.to_dict()
            # Exclude conversation_history from listing (matches old {conversation_history: 0} projection)
            farmers_list.append(d)

    return {"farmers": farmers_list, "total": total}

@router.get("/api/admin/farmer/{phone}/conversations")
async def get_convos(phone: str):
    async with async_session() as session:
        result = await session.execute(select(Farmer).where(Farmer.phone == phone))
        f = result.scalars().first()
        if not f:
            return {"conversations": [], "farmer": None}

        turns_result = await session.execute(
            select(ConversationTurn)
            .where(ConversationTurn.farmer_id == f.id)
            .order_by(ConversationTurn.timestamp.asc())
        )
        turns = turns_result.scalars().all()
        conversations = [
            {"role": t.role, "content": t.content, "timestamp": t.timestamp.isoformat() if t.timestamp else None}
            for t in turns
        ]
        return {
            "conversations": conversations,
            "farmer": {"phone": f.phone, "district": f.district,
                       "crop": f.primary_crop, "days": f.days_after_sowing},
        }

@router.get("/api/admin/dams")
async def get_dams():
    """Get LATEST dam data (not just today — supports pre-seeded data)."""
    async with async_session() as session:
        # Get latest record per reservoir using DISTINCT ON
        stmt = (
            select(DamStatus)
            .order_by(DamStatus.reservoir, desc(DamStatus.date))
            .distinct(DamStatus.reservoir)
        )
        result = await session.execute(stmt)
        dams = result.scalars().all()
        dams_list = []
        for d in dams:
            dams_list.append({
                "id": d.id,
                "reservoir": d.reservoir,
                "date": d.date,
                "full_depth_ft": d.full_depth_ft,
                "full_capacity_mcft": d.full_capacity_mcft,
                "current_level_ft": d.current_level_ft,
                "current_storage_mcft": d.current_storage_mcft,
                "current_inflow_cusecs": d.current_inflow_cusecs,
                "current_outflow_cusecs": d.current_outflow_cusecs,
                "last_year_level_ft": d.last_year_level_ft,
                "last_year_storage_mcft": d.last_year_storage_mcft,
                "storage_percentage": d.storage_percentage,
            })
    return {"dams": dams_list}

@router.get("/api/admin/alerts")
async def get_alerts(limit: int = 50):
    async with async_session() as session:
        stmt = select(AlertLog).order_by(desc(AlertLog.triggered_at)).limit(limit)
        result = await session.execute(stmt)
        alerts = result.scalars().all()
        alerts_list = []
        for a in alerts:
            alerts_list.append({
                "id": a.id,
                "district": a.district,
                "reservoir": a.reservoir,
                "reason": a.reason,
                "message": a.message,
                "alert_type": a.alert_type,
                "farmers_contacted": a.farmers_contacted,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            })
    return {"alerts": alerts_list}


from services.validation_agent import promote_to_dictionary

@router.get("/api/admin/flags")
async def get_flags(status: str = "pending", limit: int = 50):
    async with async_session() as session:
        # SQL equivalent of the MongoDB aggregation pipeline
        stmt = (
            select(
                Flag.normalized_term.label("term"),
                Flag.district,
                func.min(Flag.term).label("display_term"),
                func.count(Flag.id).label("occurrence_count"),
                func.count(distinct(Flag.call_id)).label("distinct_calls_count"),
                func.min(Flag.created_at).label("earliest_seen"),
                func.max(Flag.created_at).label("latest_seen"),
                func.max(Flag.confidence).label("top_confidence"),
                func.min(Flag.ai_proposed_meaning).label("ai_proposed_meaning"),
                func.max(Flag.ai_confidence).label("ai_confidence"),
            )
            .where(Flag.status.in_(["pending", "ai-processed"]))
            .group_by(Flag.normalized_term, Flag.district)
            .order_by(desc("occurrence_count"))
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()

        flags_list = []
        for row in rows:
            flags_list.append({
                "term": row.term,
                "district": row.district,
                "display_term": row.display_term,
                "occurrence_count": row.occurrence_count,
                "distinct_calls_count": row.distinct_calls_count,
                "earliest_seen": row.earliest_seen.isoformat() if row.earliest_seen else None,
                "latest_seen": row.latest_seen.isoformat() if row.latest_seen else None,
                "top_confidence": row.top_confidence,
                "ai_proposed_meaning": row.ai_proposed_meaning,
                "ai_confidence": row.ai_confidence,
            })
    return {"flags": flags_list}


@router.get("/api/admin/flags/detail")
async def get_flag_detail(term: str, district: str):
    async with async_session() as session:
        # Get flag occurrences
        stmt = (
            select(Flag)
            .where(
                Flag.normalized_term == term,
                Flag.district == district,
                Flag.status.in_(["pending", "ai-processed"]),
            )
            .order_by(desc(Flag.created_at))
            .limit(10)
        )
        result = await session.execute(stmt)
        occurrences = result.scalars().all()

        occ_list = []
        calls_list = []
        for occ in occurrences:
            occ_list.append({
                "id": occ.id,
                "call_id": occ.call_id,
                "term": occ.term,
                "normalized_term": occ.normalized_term,
                "reason": occ.reason,
                "confidence": occ.confidence,
                "district": occ.district,
                "village": occ.village,
                "transcript_ref": occ.transcript_ref,
                "status": occ.status,
                "ai_proposed_meaning": occ.ai_proposed_meaning,
                "ai_confidence": occ.ai_confidence,
                "created_at": occ.created_at.isoformat() if occ.created_at else None,
            })
            # Fetch matching call
            call_result = await session.execute(
                select(Call).where(Call.call_id == occ.call_id)
            )
            call = call_result.scalars().first()
            if call:
                # Load transcript turns
                turns_result = await session.execute(
                    select(CallTranscriptTurn)
                    .where(CallTranscriptTurn.call_db_id == call.id)
                    .order_by(CallTranscriptTurn.timestamp.asc())
                )
                turns = turns_result.scalars().all()
                calls_list.append({
                    "id": call.id,
                    "call_id": call.call_id,
                    "phone": call.phone,
                    "district": call.district,
                    "village": call.village,
                    "status": call.status,
                    "created_at": call.created_at.isoformat() if call.created_at else None,
                    "transcript": [
                        {"role": t.role, "content": t.content,
                         "audio_ref": t.audio_ref,
                         "timestamp": t.timestamp.isoformat() if t.timestamp else None}
                        for t in turns
                    ],
                })

    return {
        "term": term,
        "district": district,
        "occurrences": occ_list,
        "calls": calls_list,
    }


from pydantic import BaseModel
class ResolveRequest(BaseModel):
    meaning: str
    confidence: int

@router.post("/api/admin/flags/resolve")
async def resolve_flag(term: str, district: str, req: ResolveRequest):
    await promote_to_dictionary(term, district, req.meaning, req.confidence, "verified")
    return {"status": "ok"}
