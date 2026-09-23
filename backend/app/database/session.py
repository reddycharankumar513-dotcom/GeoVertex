from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Setup Async Engine
async_connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    async_connect_args["check_same_thread"] = False

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args=async_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Setup Sync Engine (for Alembic migrations and synchronous scripts)
sync_connect_args = {}
if "sqlite" in settings.DATABASE_URL_SYNC:
    sync_connect_args["check_same_thread"] = False

sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    future=True,
    connect_args=sync_connect_args,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding an async database session for request scope."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Provides a synchronous database session."""
    db = SyncSessionLocal()
    try:
        return db
    finally:
        pass
