# backend/routers/auth.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.instagram_data import InstagramData
from models.user import User
from schemas.instagram import InstagramDataCreate
from schemas.user import UserRead, UserCreate
from services.instagram_service import sync_instagram_subscriptions

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


@router.post("/register", response_model=UserRead)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # 1) Проверяем, существует ли уже пользователь с таким telegram_user_id
    stmt = select(User).where(User.telegram_user_id == user_in.telegram_user_id)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered")

    # 2) Создаём пользователя
    new_user = User(
        telegram_user_id=user_in.telegram_user_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user