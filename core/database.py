from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,          # Чтобы в консоль выводились все SQL-запросы (для отладки, можно later выключить)
    #future=True          Режим SQLAlchemy 2.0
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессии.
    Используется как Depends(get_db) в роутерах.
    """
    async with AsyncSessionLocal() as session:
        yield session
