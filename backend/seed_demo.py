"""
seed_demo.py — ONE-TIME demo data seeder.
Run: python seed_demo.py
Safe to re-run (checks marker).
"""
import asyncio, os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client.kisan_ai
MARKER = "DEMO_SEED_V2"

async def is_seeded():
    return await db.system_flags.find_one({"_id": MARKER}) is not None

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
        {"role":"kisan","content":"நாளை மழை வாய்ப்பு உள்ளது. இன்று நீர்ப்பாசனம் செய்ய வேண்டாம். மேட்டூர் அணையில் நாற்பத்தி நான்கு சதவீதம் நீர் உள்ளது.","timestamp":_ts(2)},
        {"role":"farmer","content":"இந்த வாரம் எவ்வளவு உரம் பயன்படுத்த வேண்டும்?","timestamp":_ts(2)},
        {"role":"kisan","content":"நாற்பத்தி ஐந்து நாள் நெல் பயிருக்கு யூரியா ஐம்பது கிலோ ஒரு ஏக்கருக்கு போடுங்கள்.","timestamp":_ts(2)},
        {"role":"farmer","content":"அடுத்த பருவத்தில் எந்தப் பயிரை பயிரிடலாம்?","timestamp":_ts(1)},
        {"role":"kisan","content":"தஞ்சாவூர் மண்ணுக்கு ஏற்ற அடுத்த பயிர்: உளுந்து, எள், கம்பு.","timestamp":_ts(1)},
     ]},
    {"phone":"+919894736521","district":"Ramanathapuram","village":"Paramakudi","primary_crop":"sugarcane","days_after_sowing":60,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(5),"created_at":_ts(120),
     "conversation_history":[
        {"role":"farmer","content":"கரும்பு பயிருக்கு தண்ணீர் போடணுமா?","timestamp":_ts(5)},
        {"role":"kisan","content":"அறுபது நாள் கரும்புக்கு நீர் தேவை அதிகம். வைகை அணையில் மூன்று சதவீதம் மட்டுமே நீர் உள்ளது.","timestamp":_ts(5)},
     ]},
    {"phone":"+919843276510","district":"Madurai","village":"Melur","primary_crop":"rice","days_after_sowing":30,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(8),"created_at":_ts(96),
     "conversation_history":[
        {"role":"farmer","content":"இலைகள் மஞ்சளாக மாறுகின்றன","timestamp":_ts(8)},
        {"role":"kisan","content":"நைட்ரஜன் குறைபாடாக இருக்கலாம். யூரியா இருபத்தைந்து கிலோ போடுங்கள்.","timestamp":_ts(8)},
     ]},
    {"phone":"+919443267890","district":"Krishnagiri","village":"Hosur","primary_crop":"tomato","days_after_sowing":25,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(12),"created_at":_ts(200),
     "conversation_history":[
        {"role":"farmer","content":"தக்காளியில் பூச்சி தாக்குதல்","timestamp":_ts(12)},
        {"role":"kisan","content":"வெள்ளை ஈ தாக்குதலாக இருக்கலாம். நிம் எண்ணெய் தெளிக்கவும்.","timestamp":_ts(12)},
     ]},
    {"phone":"+919791452380","district":"Salem","village":"Attur","primary_crop":"maize","days_after_sowing":35,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(14),"created_at":_ts(180),
     "conversation_history":[
        {"role":"farmer","content":"மக்காச்சோளத்திற்கு உரம் எவ்வளவு?","timestamp":_ts(14)},
        {"role":"kisan","content":"யூரியா நாற்பது கிலோ ஒரு ஏக்கருக்கு போடுங்கள்.","timestamp":_ts(14)},
     ]},
    {"phone":"+919865143270","district":"Erode","village":"Gobichettipalayam","primary_crop":"sugarcane","days_after_sowing":90,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(18),"created_at":_ts(240),
     "conversation_history":[
        {"role":"farmer","content":"கரும்பு அறுவடை எப்போது?","timestamp":_ts(18)},
        {"role":"kisan","content":"இன்னும் ஆறு மாதம் ஆகும்.","timestamp":_ts(18)},
     ]},
    {"phone":"+919487523610","district":"Coimbatore","village":"Pollachi","primary_crop":"cotton","days_after_sowing":50,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(20),"created_at":_ts(150),
     "conversation_history":[
        {"role":"farmer","content":"பருத்தியில் பூச்சி இருக்கு","timestamp":_ts(20)},
        {"role":"kisan","content":"அமெரிக்கன் புழு இருக்கலாம். பூச்சிக்கொல்லி தெளிக்கவும்.","timestamp":_ts(20)},
     ]},
    {"phone":"+919976384521","district":"Tirunelveli","village":"Ambasamudram","primary_crop":"rice","days_after_sowing":20,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(6),"created_at":_ts(100),
     "conversation_history":[
        {"role":"farmer","content":"நாளை மழை வருமா?","timestamp":_ts(6)},
        {"role":"kisan","content":"நாளை மழை வாய்ப்பு உள்ளது. நீர்ப்பாசனம் வேண்டாம்.","timestamp":_ts(6)},
     ]},
    {"phone":"+919842753961","district":"Vellore","village":"Vaniyambadi","primary_crop":"groundnut","days_after_sowing":40,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(24),"created_at":_ts(160),
     "conversation_history":[
        {"role":"farmer","content":"நிலக்கடலை விளைச்சல் எவ்வளவு?","timestamp":_ts(24)},
        {"role":"kisan","content":"சராசரி விளைச்சல் ஒரு ஏக்கருக்கு எட்டு குவிண்டால்.","timestamp":_ts(24)},
     ]},
    {"phone":"+919952146380","district":"Dindigul","village":"Oddanchatram","primary_crop":"rice","days_after_sowing":55,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(3),"created_at":_ts(130),
     "conversation_history":[
        {"role":"farmer","content":"மேட்டூர் அணை நிலவரம்?","timestamp":_ts(3)},
        {"role":"kisan","content":"மேட்டூர் அணையில் நாற்பத்தி நான்கு சதவீதம் நீர் உள்ளது. நீர் திறப்பு நடந்துக்கொண்டிருக்கிறது.","timestamp":_ts(3)},
     ]},
    {"phone":"+919600845231","district":"Namakkal","primary_crop":None,"days_after_sowing":None,
     "language":"tamil","onboarding_complete":False,"channel":"exotel","last_called":_ts(48),"created_at":_ts(48),
     "conversation_history":[]},
    {"phone":"+919445672831","district":"Karur","primary_crop":None,"days_after_sowing":None,
     "language":"tamil","onboarding_complete":False,"channel":"exotel","last_called":_ts(72),"created_at":_ts(72),
     "conversation_history":[]},
    {"phone":"+919787412563","district":"Tiruppur","village":"Udumalpet","primary_crop":"cotton","days_after_sowing":70,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(30),"created_at":_ts(210),
     "conversation_history":[
        {"role":"farmer","content":"பருத்தி விலை எவ்வளவு?","timestamp":_ts(30)},
        {"role":"kisan","content":"சந்தை விலை பற்றிய தகவல் இல்லை. உள்ளூர் சந்தையில் விசாரியுங்கள்.","timestamp":_ts(30)},
     ]},
    {"phone":"+919894521736","district":"Cuddalore","village":"Chidambaram","primary_crop":"rice","days_after_sowing":15,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(10),"created_at":_ts(80),
     "conversation_history":[
        {"role":"farmer","content":"நெல் நாற்று நட்டாச்சு","timestamp":_ts(10)},
        {"role":"kisan","content":"பதினைந்து நாள் நாற்றுக்கு தண்ணீர் நிலையாக வைக்கவும்.","timestamp":_ts(10)},
     ]},
    {"phone":"+919443198267","district":"Nagapattinam","village":"Mayiladuthurai","primary_crop":"rice","days_after_sowing":80,
     "language":"tamil","onboarding_complete":True,"channel":"exotel","last_called":_ts(16),"created_at":_ts(190),
     "conversation_history":[
        {"role":"farmer","content":"அறுவடை எப்போது?","timestamp":_ts(16)},
        {"role":"kisan","content":"இன்னும் முப்பது நாளில் அறுவடை செய்யலாம்.","timestamp":_ts(16)},
     ]},
]

ALERTS = [
    {"district":"Tirunelveli","reservoir":"Papanasam",
     "reason":"Heavy inflow 4694 cusecs","alert_type":"auto_dam",
     "message":"பாப்பநாசம் அணையில் அதிக நீர் வரத்து. கால்வாய் பகுதி விவசாயிகள் எச்சரிக்கை.",
     "triggered_at":_ts(6)},
    {"district":"Thanjavur","reservoir":"Mettur",
     "reason":"Outflow exceeds 1000 cusecs","alert_type":"auto_dam",
     "message":"மேட்டூர் அணையிலிருந்து ஆயிரம் கன அடி நீர் திறக்கப்பட்டுள்ளது. கால்வாய் விவசாயிகள் தயாராக இருங்கள்.",
     "triggered_at":_ts(3)},
]

async def seed():
    if await is_seeded():
        print("Already seeded. To re-seed, run in MongoDB:")
        print("  db.system_flags.deleteOne({_id:'DEMO_SEED_V2'})")
        print("  db.farmers.deleteMany({channel:'exotel'})")
        print("  db.dam_status.deleteMany({})")
        print("  db.alert_log.deleteMany({})")
        return
    print("Seeding...")
    for d in DAM_DATA:
        d["scraped_at"] = datetime.utcnow()
        await db.dam_status.update_one({"reservoir":d["reservoir"],"date":d["date"]},{"$set":d},upsert=True)
    print(f"  {len(DAM_DATA)} dam records")
    n = 0
    for f in FARMERS:
        f.setdefault("sowing_date",None); f.setdefault("lat",None); f.setdefault("lon",None)
        f.setdefault("pincode",None); f.setdefault("village",None)
        if not await db.farmers.find_one({"phone":f["phone"]}):
            await db.farmers.insert_one(f); n += 1
    print(f"  {n} farmers")
    for a in ALERTS:
        await db.alert_log.insert_one(a)
    print(f"  {len(ALERTS)} alerts")
    await db.system_flags.update_one({"_id":MARKER},{"$set":{"at":datetime.utcnow()}},upsert=True)
    t = await db.farmers.count_documents({})
    print(f"Done! Total farmers: {t}")

if __name__ == "__main__":
    asyncio.run(seed())
