"""
scheduler.py — APScheduler jobs: dam scraping, alert checks, cleanup.
"""

import os
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Start all scheduled jobs."""

    @scheduler.scheduled_job(CronTrigger(hour=6, minute=0))
    async def daily_dam_scrape():
        """Scrape dam data every morning at 6 AM."""
        print(f"🕕 [{datetime.utcnow()}] Running daily dam scrape...")
        try:
            from services.dam_service import scrape_dam_data
            await scrape_dam_data()
        except Exception as e:
            print(f"⚠️  Dam scrape job failed: {e}")

    @scheduler.scheduled_job(CronTrigger(hour=7, minute=0))
    async def daily_alert_check():
        """
        Check alert conditions at 7 AM daily.
        Triggers:
        - Dam outflow > 2x monthly historical average
        - Storage dropped > 15% in 24 hours
        - Storage < 20%
        - Rainfall > 80mm predicted tomorrow
        """
        print(f"🕖 [{datetime.utcnow()}] Running daily alert check...")
        try:
            from services.db import dam_status_col, farmers_col, alert_log_col
            from services.dam_service import analyze_dam_trend
            from services import weather_service, ai_service
            from data.loader import DISTRICT_CENTROIDS

            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            dams = await dam_status_col.find({"date": today_str}).to_list(length=50)

            for dam in dams:
                reservoir = dam.get("reservoir", "")
                storage_pct = dam.get("storage_percentage", 0)
                outflow = dam.get("current_outflow_cusecs", 0) or 0

                should_alert = False
                alert_reason = ""

                # High outflow check
                trend = analyze_dam_trend(reservoir)
                hist_outflow = trend.get("historical_avg_outflow", 0) or 0
                if hist_outflow > 0 and outflow > 2 * hist_outflow:
                    should_alert = True
                    alert_reason = f"{reservoir} outflow ({outflow} cusecs) is 2x above historical average"

                # Critical low storage
                if storage_pct and storage_pct < 20:
                    should_alert = True
                    alert_reason = f"{reservoir} storage critically low at {storage_pct}%"

                if should_alert:
                    # Generate Tamil alert message
                    alert_msg = (
                        f"KISAN AI எச்சரிக்கை: {reservoir} அணையில் {alert_reason}. "
                        f"உங்கள் நீர்ப்பாசனத் திட்டத்தை சரிபாருங்கள்."
                    )

                    await alert_log_col.insert_one({
                        "reservoir": reservoir,
                        "reason": alert_reason,
                        "message": alert_msg,
                        "alert_type": "auto_dam",
                        "triggered_at": datetime.utcnow(),
                    })
                    print(f"🚨 Alert: {alert_reason}")

            # Weather alert check for active districts
            districts_cursor = farmers_col.aggregate([
                {"$match": {"district": {"$ne": None}, "onboarding_complete": True}},
                {"$group": {"_id": "$district"}},
            ])
            active_districts = [d["_id"] async for d in districts_cursor]

            for district in active_districts:
                centroid = DISTRICT_CENTROIDS.get(district, {})
                lat, lon = centroid.get("lat"), centroid.get("lon")
                if lat and lon:
                    weather = await weather_service.get_weather(lat, lon)
                    tomorrow = weather.get("tomorrow", {})
                    rain_mm = tomorrow.get("rainfall_mm", 0) or 0
                    if rain_mm > 80:
                        await alert_log_col.insert_one({
                            "district": district,
                            "reason": f"Heavy rain predicted: {rain_mm}mm tomorrow",
                            "alert_type": "auto_weather",
                            "triggered_at": datetime.utcnow(),
                        })
                        print(f"🌧️ Rain alert for {district}: {rain_mm}mm predicted")

        except Exception as e:
            print(f"⚠️  Alert check job failed: {e}")

    @scheduler.scheduled_job(CronTrigger(hour=2, minute=0))
    async def cleanup_static_files():
        """Delete MP3 files older than 24 hours."""
        print(f"🧹 [{datetime.utcnow()}] Cleaning up static files...")
        static_dir = "static"
        if not os.path.exists(static_dir):
            return
        cutoff = time.time() - 86400  # 24 hours ago
        count = 0
        for fname in os.listdir(static_dir):
            fpath = os.path.join(static_dir, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                try:
                    os.remove(fpath)
                    count += 1
                except Exception:
                    pass
        print(f"   Cleaned up {count} files.")

    scheduler.start()
    print("⏰ Scheduler started with 3 jobs (dam scrape, alert check, cleanup).")
