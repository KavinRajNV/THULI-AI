"""
database.py — SQLAlchemy async engine + session factory for PostgreSQL.
Replaces the old motor/pymongo MongoDB connection.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/thuli_ai")

# Ensure asyncpg driver prefix
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """Get a new async session — use as async context manager."""
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables (for initial setup without Alembic)."""
    from models import Base as ModelsBase  # noqa: F811
    async with engine.begin() as conn:
        await conn.run_sync(ModelsBase.metadata.create_all)
    print("✅ PostgreSQL tables created/verified.")
