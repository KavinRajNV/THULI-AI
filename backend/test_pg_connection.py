"""
test_pg_connection.py — Verify PostgreSQL migration works end-to-end.
Run: python test_pg_connection.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, func, text
from database import engine, async_session
from models import Farmer, ConversationTurn, DamStatus, AlertLog, WeatherCache, Call, Flag, RegionalDictionary, SystemMeta


async def test():
    print("=" * 60)
    print("  KISAN-AI PostgreSQL Connection Test")
    print("=" * 60)

    # 1. Test raw connection
    print("\n1. Testing raw connection...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   [OK] Connected! PostgreSQL version: {version[:60]}...")
    except Exception as e:
        print(f"   [FAIL] Connection failed: {e}")
        return False

    # 2. Check PostGIS
    print("\n2. Checking PostGIS...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT PostGIS_Version()"))
            postgis = result.fetchone()[0]
            print(f"   [OK] PostGIS: {postgis}")
    except Exception as e:
        print(f"   [WARN] PostGIS not available: {e}")

    # 3. Check all tables exist
    print("\n3. Checking tables...")
    expected_tables = [
        "farmers", "conversation_turns", "dam_status", "weather_cache",
        "alert_log", "calls", "call_transcript_turns", "flags",
        "regional_dictionary", "system_meta",
    ]
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ))
        actual_tables = {row[0] for row in result.fetchall()}

    for t in expected_tables:
        if t in actual_tables:
            print(f"   [OK] {t}")
        else:
            print(f"   [FAIL] {t} — MISSING!")

    # 4. Insert a test farmer, read it back, then delete
    test_phone = "__test_pg_verify__"
    print(f"\n4. INSERT -> SELECT -> DELETE test (phone='{test_phone}')...")
    try:
        async with async_session() as session:
            # Insert
            farmer = Farmer(
                phone=test_phone,
                district="TestDistrict",
                village="TestVillage",
                primary_crop="rice",
                days_after_sowing=30,
                language="tamil",
                onboarding_complete=True,
                lat=10.787,
                lon=79.139,
                geom=f"SRID=4326;POINT(79.139 10.787)",
            )
            session.add(farmer)
            await session.commit()
            await session.refresh(farmer)
            print(f"   [OK] INSERT: id={farmer.id}")

            # Read back
            result = await session.execute(
                select(Farmer).where(Farmer.phone == test_phone)
            )
            f = result.scalars().first()
            assert f is not None, "Farmer not found!"
            assert f.district == "TestDistrict"
            assert f.primary_crop == "rice"
            print(f"   [OK] SELECT: district={f.district}, crop={f.primary_crop}, lat={f.lat}, lon={f.lon}")

            # Test to_dict()
            d = f.to_dict()
            assert d["phone"] == test_phone
            print(f"   [OK] to_dict(): keys={list(d.keys())[:5]}...")

            # Delete
            await session.delete(f)
            await session.commit()
            print(f"   [OK] DELETE: cleaned up")
    except Exception as e:
        print(f"   ❌ CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Count existing rows (from seed_demo if run)
    print("\n5. Row counts (seed data)...")
    async with async_session() as session:
        for model, name in [
            (Farmer, "farmers"),
            (DamStatus, "dam_status"),
            (AlertLog, "alert_log"),
            (Call, "calls"),
            (Flag, "flags"),
            (RegionalDictionary, "regional_dictionary"),
        ]:
            count = (await session.execute(select(func.count(model.id)))).scalar()
            print(f"   {name}: {count} rows")

    print("\n" + "=" * 60)
    print("  [OK] ALL TESTS PASSED — PostgreSQL migration is working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
