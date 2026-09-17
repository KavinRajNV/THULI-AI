"""
services/db.py — Database session provider.
Migrated from MongoDB (motor) to PostgreSQL (SQLAlchemy async).
"""
from database import async_session, engine

async def get_session():
    async with async_session() as session:
        async with session.begin():
            yield session
