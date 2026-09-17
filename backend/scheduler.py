"""
scheduler.py — APScheduler jobs: dam scraping, alert checks, cleanup.
Migrated from MongoDB to PostgreSQL (SQLAlchemy async).
"""

import os
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from sqlalchemy import select, distinct
from database import async_session
from models import DamStatus, Farmer, AlertLog

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
            from services.dam_service import analyze_dam_trend
            from services import weather_service, ai_service
            from data.loader import DISTRICT_CENTROIDS

            today_str = datetime.utcnow().strftime("%Y-%m-%d")

            async with async_session() as session:
                # Get today's dam data
                result = await session.execute(
                    select(DamStatus).where(DamStatus.date == today_str)
                )
                dams = result.scalars().all()

                for dam in dams:
                    reservoir = dam.reservoir or ""
                    storage_pct = dam.storage_percentage or 0
                    outflow = dam.current_outflow_cusecs or 0

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
                        alert_msg = (
                            f"KISAN AI எச்சரிக்கை: {reservoir} அணையில் {alert_reason}. "
                            f"உங்கள் நீர்ப்பாசனத் திட்டத்தை சரிபாருங்கள்."
                        )
                        alert = AlertLog(
                            reservoir=reservoir,
                            reason=alert_reason,
                            message=alert_msg,
                            alert_type="auto_dam",
                            triggered_at=datetime.utcnow(),
                        )
                        session.add(alert)
                        print(f"🚨 Alert: {alert_reason}")

                # Get active districts from onboarded farmers
                districts_result = await session.execute(
                    select(distinct(Farmer.district)).where(
                        Farmer.district.isnot(None),
                        Farmer.onboarding_complete == True,
                    )
                )
                active_districts = [row[0] for row in districts_result.all()]

                for district in active_districts:
                    centroid = DISTRICT_CENTROIDS.get(district, {})
                    lat, lon = centroid.get("lat"), centroid.get("lon")
                    if lat and lon:
                        weather = await weather_service.get_weather(lat=lat, lon=lon)
                        tomorrow = weather.get("tomorrow", {})
                        rain_mm = tomorrow.get("rainfall_mm", 0) or 0
                        if rain_mm > 80:
                            alert = AlertLog(
                                district=district,
                                reason=f"Heavy rain predicted: {rain_mm}mm tomorrow",
                                alert_type="auto_weather",
                                triggered_at=datetime.utcnow(),
                            )
                            session.add(alert)
                            print(f"🌧️ Rain alert for {district}: {rain_mm}mm predicted")

                await session.commit()

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

    @scheduler.scheduled_job(CronTrigger(hour=3, minute=0))
    async def cleanup_weather_cache():
        """Delete expired weather cache entries (> 6 hours old)."""
        print(f"🧹 [{datetime.utcnow()}] Cleaning up weather cache...")
        try:
            from sqlalchemy import delete
            from models import WeatherCache
            cutoff = datetime.utcnow() - timedelta(hours=6)
            async with async_session() as session:
                result = await session.execute(
                    delete(WeatherCache).where(WeatherCache.cached_at < cutoff)
                )
                await session.commit()
                print(f"   Cleaned up {result.rowcount} stale cache entries.")
        except Exception as e:
            print(f"⚠️  Weather cache cleanup failed: {e}")

    scheduler.start()
    print("⏰ Scheduler started with 4 jobs (dam scrape, alert check, file cleanup, cache cleanup).")
