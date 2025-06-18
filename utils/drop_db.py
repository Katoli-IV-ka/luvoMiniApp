from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from core.config import settings

from models.base import Base


async def async_drop_database():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        isolation_level="AUTOCOMMIT"
    )
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
        await conn.execute(text("SET search_path TO public"))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("⚠️ Схема public очищена и все таблицы созданы заново.")