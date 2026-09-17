"""
seed_demo.py — ONE-TIME demo data seeder for PostgreSQL.
Run: python seed_demo.py
Safe to re-run (checks marker).
"""
import asyncio, os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import async_session
from models import DamStatus, Farmer, ConversationTurn, AlertLog, SystemMeta

MARKER = "DEMO_SEED_V2"

async def is_seeded():
    async with async_session() as session:
        result = await session.execute(select(SystemMeta).where(SystemMeta.key == MARKER))
        return result.scalars().first() is not None

def _ts(h):
    return datetime.utcnow() - timedelta(hours=h)

# ═══ DAM DATA (June 13 finale) — stored as "latest" ═══════════════════
DAM_DATA = [
    {"reservoir":"Mettur","date":"2026-06-13","full_depth_ft":120,"full_capacity_mcft":93470,
     "current_level_ft":79.75,"current_storage_mcft":41708,
     "current_inflow_cusecs":772,"current_outflow_cusecs":1003,
     "last_year_level_ft":114.16,"last_year_storage_mcft":84461,
     "storage_percentage":44.6},
    {"reservoir":"Bhavanisagar","date":"2026-06-13","full_depth_ft":105,"full_capacity_mcft":32800,
     "current_level_ft":55.37,"current_storage_mcft":5850,
     "current_inflow_cusecs":156,"current_outflow_cusecs":850,
     "last_year_level_ft":83.09,"last_year_storage_mcft":17379,
     "storage_percentage":17.8},
    {"reservoir":"Amaravathi","date":"2026-06-13","full_depth_ft":90,"full_capacity_mcft":4047,
     "current_level_ft":37.04,"current_storage_mcft":625,
     "current_inflow_cusecs":532,"current_outflow_cusecs":0,
     "last_year_level_ft":83.27,"last_year_storage_mcft":3451,
     "storage_percentage":15.5},
    {"reservoir":"Vaigai","date":"2026-06-13","full_depth_ft":71,"full_capacity_mcft":6091,
     "current_level_ft":24.02,"current_storage_mcft":184,
     "current_inflow_cusecs":273,"current_outflow_cusecs":69,
     "last_year_level_ft":59.32,"last_year_storage_mcft":3478,
     "storage_percentage":3.0},
    {"reservoir":"Papanasam","date":"2026-06-13","full_depth_ft":143,"full_capacity_mcft":5500,
     "current_level_ft":75.4,"current_storage_mcft":1860,
     "current_inflow_cusecs":4694,"current_outflow_cusecs":405,
     "last_year_level_ft":125.3,"last_year_storage_mcft":4435,
     "storage_percentage":33.8},
    {"reservoir":"Manimuthar","date":"2026-06-13","full_depth_ft":118,"full_capacity_mcft":5511,
     "current_level_ft":69.42,"current_storage_mcft":1507,
     "current_inflow_cusecs":786,"current_outflow_cusecs":195,
     "last_year_level_ft":93,"last_year_storage_mcft":3176,
     "storage_percentage":27.3},
    {"reservoir":"Krishnagiri","date":"2026-06-13","full_depth_ft":52,"full_capacity_mcft":1666,
     "current_level_ft":49.8,"current_storage_mcft":1421,
     "current_inflow_cusecs":369,"current_outflow_cusecs":369,
     "last_year_level_ft":50.95,"last_year_storage_mcft":1546,
     "storage_percentage":85.3},
]

# ═══ REALISTIC TN PHONE FARMERS ═══════════════════════════════════════
FARMERS = [
    {"phone":"+919944523601","district":"Thanjavur","village":"Orathanadu","pincode":"614625",
     "primary_crop":"rice","days_after_sowing":45,"language":"tamil",
     "onboarding_complete":True,"channel":"exotel","last_called":_ts(2),"created_at":_ts(72),
     "conversation_history":[
        {"role":"farmer","content":"613001","timestamp":_ts(72)},
        {"role":"kisan","content":"நன்றி! Thanjavur மாவட்டம் பதிவு. என்ன பயிர் சாகுபடி செய்கிறீர்கள்?","timestamp":_ts(72)},
        {"role":"farmer","content":"நெல். 45 நாள் ஆகிறது.","timestamp":_ts(71)},
        {"role":"kisan","content":"அருமை! Thanjavur - rice, 45 நாள். கேள்வி கேளுங்கள்!","timestamp":_ts(71)},
        {"role":"farmer","content":"என் நெல் வயலுக்கு இன்று தண்ணீர் பாய்ச்சலாமா?","timestamp":_ts(2)},
        {"role":"kisan","content":"நாளை மழை வாய்ப்பு உள்ளது. இன்று நீர்ப்பாசனம் செய்ய வேண்டாம்.","timestamp":_ts(2)},
     ]},
    {"phone":"+919894736521","district":"Ramanathapuram","village":"Paramakudi","primary_crop":"sugarcane","days_after_sowing":60,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(5),"created_at":_ts(120),
     "conversation_history":[
        {"role":"farmer","content":"கரும்பு பயிருக்கு தண்ணீர் போடணுமா?","timestamp":_ts(5)},
        {"role":"kisan","content":"அறுபது நாள் கரும்புக்கு நீர் தேவை அதிகம்.","timestamp":_ts(5)},
     ]},
    {"phone":"+919843276510","district":"Madurai","village":"Melur","primary_crop":"rice","days_after_sowing":30,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(8),"created_at":_ts(96),
     "conversation_history":[
        {"role":"farmer","content":"இலைகள் மஞ்சளாக மாறுகின்றன","timestamp":_ts(8)},
        {"role":"kisan","content":"நைட்ரஜன் குறைபாடாக இருக்கலாம்.","timestamp":_ts(8)},
     ]},
    {"phone":"+919443267890","district":"Krishnagiri","village":"Hosur","primary_crop":"tomato","days_after_sowing":25,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(12),"created_at":_ts(200),
     "conversation_history":[]},
    {"phone":"+919791452380","district":"Salem","village":"Attur","primary_crop":"maize","days_after_sowing":35,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(14),"created_at":_ts(180),
     "conversation_history":[]},
    {"phone":"+919865143270","district":"Erode","village":"Gobichettipalayam","primary_crop":"sugarcane","days_after_sowing":90,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(18),"created_at":_ts(240),
     "conversation_history":[]},
    {"phone":"+919487523610","district":"Coimbatore","village":"Pollachi","primary_crop":"cotton","days_after_sowing":50,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(20),"created_at":_ts(150),
     "conversation_history":[]},
    {"phone":"+919976384521","district":"Tirunelveli","village":"Ambasamudram","primary_crop":"rice","days_after_sowing":20,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(6),"created_at":_ts(100),
     "conversation_history":[]},
    {"phone":"+919842753961","district":"Vellore","village":"Vaniyambadi","primary_crop":"groundnut","days_after_sowing":40,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(24),"created_at":_ts(160),
     "conversation_history":[]},
    {"phone":"+919952146380","district":"Dindigul","village":"Oddanchatram","primary_crop":"rice","days_after_sowing":55,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(3),"created_at":_ts(130),
     "conversation_history":[]},
    {"phone":"+919600845231","district":"Namakkal","primary_crop":None,"days_after_sowing":None,
     "language":"tamil","onboarding_complete":False,"channel":"exotel","last_called":_ts(48),"created_at":_ts(48),
     "conversation_history":[]},
    {"phone":"+919445672831","district":"Karur","primary_crop":None,"days_after_sowing":None,
     "language":"tamil","onboarding_complete":False,"channel":"exotel","last_called":_ts(72),"created_at":_ts(72),
     "conversation_history":[]},
    {"phone":"+919787412563","district":"Tiruppur","village":"Udumalpet","primary_crop":"cotton","days_after_sowing":70,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(30),"created_at":_ts(210),
     "conversation_history":[]},
    {"phone":"+919894521736","district":"Cuddalore","village":"Chidambaram","primary_crop":"rice","days_after_sowing":15,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(10),"created_at":_ts(80),
     "conversation_history":[]},
    {"phone":"+919443198267","district":"Nagapattinam","village":"Mayiladuthurai","primary_crop":"rice","days_after_sowing":80,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(16),"created_at":_ts(190),
     "conversation_history":[]},
]

ALERTS = [
    {"district":"Tirunelveli","reservoir":"Papanasam",
     "reason":"Heavy inflow 4694 cusecs","alert_type":"auto_dam",
     "message":"பாப்பநாசம் அணையில் அதிக நீர் வரத்து. கால்வாய் பகுதி விவசாயிகள் எச்சரிக்கை.",
     "triggered_at":_ts(6)},
    {"district":"Thanjavur","reservoir":"Mettur",
     "reason":"Outflow exceeds 1000 cusecs","alert_type":"auto_dam",
     "message":"மேட்டூர் அணையிலிருந்து ஆயிரம் கன அடி நீர் திறக்கப்பட்டுள்ளது.",
     "triggered_at":_ts(3)},
]

async def seed():
    if await is_seeded():
        print("Already seeded. To re-seed, run in PostgreSQL:")
        print("  DELETE FROM system_meta WHERE key = 'DEMO_SEED_V2';")
        print("  DELETE FROM farmers WHERE channel = 'exotel';")
        print("  DELETE FROM dam_status;")
        print("  DELETE FROM alert_log;")
        return

    print("Seeding PostgreSQL...")

    async with async_session() as session:
        # Seed dam data
        for d in DAM_DATA:
            d["scraped_at"] = datetime.utcnow()
            stmt = pg_insert(DamStatus).values(**d)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_dam_reservoir_date",
                set_={k: v for k, v in d.items() if k not in ("reservoir", "date")}
            )
            await session.execute(stmt)
        print(f"  {len(DAM_DATA)} dam records")

        # Seed farmers
        n = 0
        for f_data in FARMERS:
            conversation_history = f_data.pop("conversation_history", [])
            f_data.setdefault("sowing_date", None)
            f_data.setdefault("lat", None)
            f_data.setdefault("lon", None)
            f_data.setdefault("pincode", None)
            f_data.setdefault("village", None)

            # Check if farmer exists
            result = await session.execute(
                select(Farmer).where(Farmer.phone == f_data["phone"])
            )
            existing = result.scalars().first()
            if not existing:
                farmer = Farmer(**f_data)
                session.add(farmer)
                await session.flush()  # Get the farmer.id

                # Insert conversation turns
                for turn in conversation_history:
                    ct = ConversationTurn(
                        farmer_id=farmer.id,
                        role=turn["role"],
                        content=turn["content"],
                        timestamp=turn["timestamp"],
                    )
                    session.add(ct)
                n += 1
        print(f"  {n} farmers")

        # Seed alerts
        for a in ALERTS:
            alert = AlertLog(**a)
            session.add(alert)
        print(f"  {len(ALERTS)} alerts")

        # Set seed marker
        stmt = pg_insert(SystemMeta).values(
            key=MARKER, value={"at": datetime.utcnow().isoformat()}
        ).on_conflict_do_update(
            index_elements=["key"],
            set_={"value": {"at": datetime.utcnow().isoformat()}}
        )
        await session.execute(stmt)

        await session.commit()

    # Count total farmers
    async with async_session() as session:
        from sqlalchemy import func
        total = (await session.execute(select(func.count(Farmer.id)))).scalar()
        print(f"Done! Total farmers: {total}")

if __name__ == "__main__":
    asyncio.run(seed())
