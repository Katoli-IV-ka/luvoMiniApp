import asyncio
import logging
from core.database import engine
from models.base import Base

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def async_reset_database():
    log.info("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, checkfirst=True)

    log.info("Recreating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    log.info("Database schema has been reset.")


def reset_database():
    asyncio.run(async_reset_database())


if __name__ == "__main__":
    reset_database()