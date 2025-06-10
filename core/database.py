from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,          # Чтобы в консоль выводились все SQL-запросы (для отладки, можно later выключить)
    future=True         # Режим SQLAlchemy 2.0
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False,)


async def get_db() -> AsyncSession:
    """
    Используйте в роутерах:
        async def some_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
