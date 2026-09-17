"""
models.py — SQLAlchemy ORM models for KISAN-AI / Thuli-AI.
Normalized PostgreSQL schema replacing all MongoDB collections.
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography

from database import Base


# ═══════════════════════════════════════════════════════════════════════
# 1. FARMERS  (was: MongoDB `farmers` collection)
# ═══════════════════════════════════════════════════════════════════════
class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(50), unique=True, nullable=False, index=True)
    pincode = Column(String(6), nullable=True)
    district = Column(String(100), nullable=True, index=True)
    village = Column(String(200), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    # PostGIS geography column — auto-computed from lat/lon on insert/update
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    primary_crop = Column(String(100), nullable=True)
    sowing_date = Column(DateTime, nullable=True)
    days_after_sowing = Column(Integer, nullable=True)
    language = Column(String(20), nullable=False, default="tamil")
    onboarding_complete = Column(Boolean, nullable=False, default=False)
    channel = Column(String(50), nullable=True)
    last_called = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    conversation_turns = relationship(
        "ConversationTurn", back_populates="farmer",
        cascade="all, delete-orphan", order_by="ConversationTurn.timestamp",
    )

    def to_dict(self):
        """Convert to dict matching the old MongoDB document shape."""
        return {
            "id": self.id,
            "phone": self.phone,
            "pincode": self.pincode,
            "district": self.district,
            "village": self.village,
            "lat": self.lat,
            "lon": self.lon,
            "primary_crop": self.primary_crop,
            "sowing_date": self.sowing_date.isoformat() if self.sowing_date else None,
            "days_after_sowing": self.days_after_sowing,
            "language": self.language,
            "onboarding_complete": self.onboarding_complete,
            "channel": self.channel,
            "last_called": self.last_called.isoformat() if self.last_called else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════
# 2. CONVERSATION TURNS  (was: farmers.conversation_history[])
# ═══════════════════════════════════════════════════════════════════════
class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)   # "farmer" | "kisan"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="conversation_turns")


# ═══════════════════════════════════════════════════════════════════════
# 3. DAM STATUS  (was: MongoDB `dam_status` collection)
# ═══════════════════════════════════════════════════════════════════════
class DamStatus(Base):
    __tablename__ = "dam_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reservoir = Column(String(200), nullable=False)
    date = Column(String(10), nullable=False)               # "YYYY-MM-DD"
    full_depth_ft = Column(Float, nullable=True)
    full_capacity_mcft = Column(Float, nullable=True)
    current_level_ft = Column(Float, nullable=True)
    current_storage_mcft = Column(Float, nullable=True)
    current_inflow_cusecs = Column(Float, nullable=True)
    current_outflow_cusecs = Column(Float, nullable=True)
    last_year_level_ft = Column(Float, nullable=True)
    last_year_storage_mcft = Column(Float, nullable=True)
    storage_percentage = Column(Float, nullable=True)
    scraped_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("reservoir", "date", name="uq_dam_reservoir_date"),
        Index("ix_dam_date", "date"),
    )


# ═══════════════════════════════════════════════════════════════════════
# 4. WEATHER CACHE  (was: MongoDB `weather_cache` collection)
# ═══════════════════════════════════════════════════════════════════════
class WeatherCache(Base):
    __tablename__ = "weather_cache"

    cache_key = Column(String(100), primary_key=True)   # "openmeteo_10.79_79.14"
    data = Column(JSONB, nullable=True)                 # Full forecast dict
    cached_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════
# 5. ALERT LOG  (was: MongoDB `alert_log` collection)
# ═══════════════════════════════════════════════════════════════════════
class AlertLog(Base):
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district = Column(String(100), nullable=True)
    reservoir = Column(String(200), nullable=True)
    reason = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    alert_type = Column(String(50), nullable=False)       # "auto_dam" | "auto_weather" | "manual"
    farmers_contacted = Column(Integer, nullable=True)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


# ═══════════════════════════════════════════════════════════════════════
# 6. CALLS  (was: MongoDB `calls` collection)
# ═══════════════════════════════════════════════════════════════════════
class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    district = Column(String(100), nullable=True)
    village = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="in-progress")

    # Relationships
    transcript_turns = relationship(
        "CallTranscriptTurn", back_populates="call",
        cascade="all, delete-orphan", order_by="CallTranscriptTurn.timestamp",
    )


# ═══════════════════════════════════════════════════════════════════════
# 7. CALL TRANSCRIPT TURNS  (was: calls.transcript[])
# ═══════════════════════════════════════════════════════════════════════
class CallTranscriptTurn(Base):
    __tablename__ = "call_transcript_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_db_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)              # "farmer" | "kisan"
    content = Column(Text, nullable=False)
    audio_ref = Column(String(500), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    call = relationship("Call", back_populates="transcript_turns")


# ═══════════════════════════════════════════════════════════════════════
# 8. FLAGS  (was: MongoDB `flags` collection)
# ═══════════════════════════════════════════════════════════════════════
class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String(200), nullable=False, index=True)   # logical ref to calls.call_id
    term = Column(String(500), nullable=False)
    normalized_term = Column(String(500), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    district = Column(String(100), nullable=False, index=True)
    village = Column(String(200), nullable=True)
    transcript_ref = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    ai_proposed_meaning = Column(Text, nullable=True)
    ai_confidence = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════
# 9. REGIONAL DICTIONARY  (was: MongoDB `regional_dictionary` collection)
# ═══════════════════════════════════════════════════════════════════════
class RegionalDictionary(Base):
    __tablename__ = "regional_dictionary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(500), nullable=False)
    district = Column(String(100), nullable=False)
    standard_meaning = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)            # "verified" | "ai-verified-pending-audit"
    last_confirmed_confidence = Column(Integer, nullable=True)
    occurrence_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("district", "term", name="uq_regional_dict_district_term"),
    )


# ═══════════════════════════════════════════════════════════════════════
# 10. SYSTEM META  (was: MongoDB `system_flags` collection)
# ═══════════════════════════════════════════════════════════════════════
class SystemMeta(Base):
    __tablename__ = "system_meta"

    key = Column(String(200), primary_key=True)
    value = Column(JSONB, nullable=True)
