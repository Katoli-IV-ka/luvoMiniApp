# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.user import User
from schemas.user import UserRead, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserRead)
async def login_or_register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Пример: клиент отправляет JSON {"telegram_user_id": 12345}.
    Если пользователь с таким telegram_user_id есть → вернуть его.
    Иначе → создать и вернуть.
    (В реальности здесь будет проверка initData из Telegram WebApp.)
    """
    stmt = select(User).where(User.telegram_user_id == user_in.telegram_user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Создаём нового пользователя
        new_user = User(telegram_user_id=user_in.telegram_user_id)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    return user


@router.get("/me", response_model=UserRead)
async def get_current_user(
    # В реальности сюда передавался бы декодированный токен с telegram_user_id
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
