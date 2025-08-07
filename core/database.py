from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from .config import settings

print(">>> DEBUG: raw DATABASE_URL =", settings.DATABASE_URL)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,      # <— добавили проверку соединения перед использованием
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
