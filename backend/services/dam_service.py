"""
services/dam_service.py — Dam data with direct name lookup.
When farmer says "மேட்டூர்", fetches Mettur directly (no district mapping needed).
"""
import re, os
from datetime import datetime
import httpx, pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import async_session
from models import DamStatus
import data.loader

# Dam name variants (Tamil + English + Tanglish)
DAM_NAMES = {
    "mettur": "Mettur", "மேட்டூர்": "Mettur", "மேட்டூர": "Mettur",
    "bhavanisagar": "Bhavanisagar", "பவானிசாகர்": "Bhavanisagar", "பவானி": "Bhavanisagar",
    "amaravathi": "Amaravathi", "அமராவதி": "Amaravathi", "அமராவதி": "Amaravathi",
    "vaigai": "Vaigai", "வைகை": "Vaigai",
    "papanasam": "Papanasam", "பாப்பநாசம்": "Papanasam",
    "manimuthar": "Manimuthar", "மணிமுத்தாறு": "Manimuthar",
    "krishnagiri": "Krishnagiri", "கிருஷ்ணகிரி": "Krishnagiri",
}

def extract_dam_name(text):
    """Extract a specific dam name from farmer's text."""
    tl = text.lower()
    for key, name in DAM_NAMES.items():
        if key.lower() in tl or key in text:
            return name
    return None


async def get_dam_by_name(dam_name):
    """Fetch dam data directly by name from PostgreSQL."""
    async with async_session() as session:
        result = await session.execute(
            select(DamStatus)
            .where(DamStatus.reservoir.ilike(f"%{dam_name}%"))
            .order_by(DamStatus.date.desc())
            .limit(1)
        )
        status = result.scalars().first()
        
    if not status:
        return None
    trend = analyze_dam_trend(dam_name)
    return {
        "dam_name": dam_name,
        "storage_pct": status.storage_percentage,
        "inflow": status.current_inflow_cusecs,
        "outflow": status.current_outflow_cusecs,
        "current_storage_mcft": status.current_storage_mcft,
        "full_capacity_mcft": status.full_capacity_mcft,
        "last_year_storage_mcft": status.last_year_storage_mcft,
        "data_date": status.date,
        "historical": trend,
        "historical_note": trend.get("note", ""),
    }


async def get_dam_context(district=None, farmer_text=""):
    """Get dam data — by name first, then by district."""
    # Priority 1: specific dam name in text
    specific = extract_dam_name(farmer_text)
    if specific:
        result = await get_dam_by_name(specific)
        if result:
            print(f"  Dam: direct lookup {specific}")
            return result

    # Priority 2: district mapping
    if district:
        dl = district.lower().strip()
        dam_json = data.loader.DAM_IRRIGATION_DATA
        entries = dam_json if isinstance(dam_json, list) else (
            list(dam_json.values()) if isinstance(dam_json, dict) else [])
        for entry in entries:
            if not isinstance(entry, dict): continue
            bene = entry.get("beneficiary_districts", entry.get("districts", []))
            if isinstance(bene, str): bene = [bene]
            if isinstance(bene, list) and any(dl in str(b).lower() for b in bene):
                dn = entry.get("dam_name", entry.get("name", "Unknown"))
                result = await get_dam_by_name(dn)
                if result:
                    print(f"  Dam: district mapping {district} -> {dn}")
                    return result

    # Priority 3: if specific dam found but no MongoDB data, return what we know
    if specific:
        return {"dam_name": specific, "note": f"No current data for {specific}",
                "historical": analyze_dam_trend(specific)}

    return {"note": f"No dam data for {district or 'unknown district'}"}


def analyze_dam_trend(dam_name):
    rdf = data.loader.RESERVOIR_DF
    if rdf.empty:
        return {"note": "No historical data", "confidence": "low",
                "historical_avg_storage_pct": None, "release_likely": False}
    res_col = next((c for c in ["reservoir", "Reservoir"] if c in rdf.columns), None)
    if not res_col: return {"note": "Column missing", "confidence": "low"}
    mask = rdf[res_col].str.lower().str.contains(dam_name.lower(), na=False)
    ddf = rdf[mask]
    if ddf.empty: return {"note": f"No history for {dam_name}", "confidence": "low"}
    month = datetime.utcnow().month
    date_col = next((c for c in ["date","Date"] if c in ddf.columns), None)
    if date_col:
        mdf = ddf[pd.to_datetime(ddf[date_col], errors="coerce").dt.month == month]
        if mdf.empty: mdf = ddf
    else: mdf = ddf
    sp = next((c for c in ["storage_percentage"] if c in mdf.columns), None)
    if not sp and "storage_mcft" in mdf.columns and "full_capacity_mcft" in mdf.columns:
        mdf = mdf.copy(); mdf["storage_percentage"] = (mdf["storage_mcft"]/mdf["full_capacity_mcft"]*100).round(2); sp = "storage_percentage"
    hs = mdf[sp].dropna() if sp else pd.Series()
    oc = next((c for c in ["outflow_cusecs"] if c in mdf.columns), None)
    ho = mdf[oc].dropna() if oc else pd.Series()
    return {
        "historical_avg_storage_pct": round(float(hs.mean()),1) if len(hs)>0 else None,
        "release_likely": float(ho.mean())>500 if len(ho)>0 else False,
        "confidence": "high" if len(mdf)>=50 else "medium" if len(mdf)>=20 else "low",
        "note": f"Based on {len(mdf)} records",
    }

async def scrape_dam_data():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"https://tnagriculture.in/ARS/home/reservoir/{today}",
                headers={"User-Agent":"Mozilla/5.0 Chrome/124.0"})
            r.raise_for_status()
        soup = BeautifulSoup(r.text,"html.parser"); table = soup.find("table")
        if not table: return []
        results = []
        async with async_session() as session:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells)<9: continue
                raw = re.sub(r"\*+","",cells[0].get_text(strip=True)).strip()
                fc = _sf(cells[2].get_text()); cs = _sf(cells[4].get_text())
                sp = round(cs/fc*100,1) if fc and fc>0 and cs else 0
                rec = {"reservoir":raw,"date":today,"full_capacity_mcft":fc,"current_storage_mcft":cs,
                    "current_inflow_cusecs":_sf(cells[5].get_text()),"current_outflow_cusecs":_sf(cells[6].get_text()),
                    "storage_percentage":sp,"scraped_at":datetime.utcnow()}
                
                stmt = pg_insert(DamStatus).values(
                    reservoir=raw,
                    date=today,
                    full_capacity_mcft=fc,
                    current_storage_mcft=cs,
                    current_inflow_cusecs=_sf(cells[5].get_text()),
                    current_outflow_cusecs=_sf(cells[6].get_text()),
                    storage_percentage=sp,
                    scraped_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=['date', 'reservoir'],
                    set_={
                        'full_capacity_mcft': fc,
                        'current_storage_mcft': cs,
                        'current_inflow_cusecs': _sf(cells[5].get_text()),
                        'current_outflow_cusecs': _sf(cells[6].get_text()),
                        'storage_percentage': sp,
                        'scraped_at': datetime.utcnow()
                    }
                )
                await session.execute(stmt)
                results.append(rec)
            await session.commit()
        print(f"Scraped {len(results)} dams")
        return results
    except Exception as e:
        print(f"Scrape failed: {e}"); return []

def _sf(v):
    try: return float(str(v).replace(",","").strip())
    except: return None
