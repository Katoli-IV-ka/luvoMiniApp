import asyncio
import logging
from core.database import engine
from models.base import Base

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def async_drop_database():
    log.info("Dropping all tables (async)...")
    # Открываем транзакцию и выполняем синхронные операции через run_sync
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    log.info("Database schema has been reset (async).")


