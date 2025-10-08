"""Утилиты для преобразования моделей пользователей в схемы Pydantic."""
from collections.abc import Iterable
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.user import TopUserRead, UserRead
from utils.s3 import build_photo_urls


async def to_user_read(user: User, db: AsyncSession) -> UserRead:
    """Сконвертировать модель пользователя в UserRead со списком фото."""
    photos = await build_photo_urls(user.id, db)
    return UserRead(
        user_id=user.id,
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        birthdate=user.birthdate,
        gender=user.gender,
        about=user.about,
        photos=photos,
        latitude=user.latitude,
        longitude=user.longitude,
        telegram_username=user.telegram_username,
        instagram_username=user.instagram_username,
        is_premium=user.is_premium,
        premium_expires_at=user.premium_expires_at,
        created_at=user.created_at,
    )


async def to_user_reads(users: Iterable[User], db: AsyncSession) -> List[UserRead]:
    """Сконвертировать список моделей пользователей в UserRead."""
    return [await to_user_read(user, db) for user in users]


async def to_top_user_read(
    user: User, likes_count: int, db: AsyncSession
) -> TopUserRead:
    """Сконвертировать модель пользователя в TopUserRead."""
    photos = await build_photo_urls(user.id, db)
    return TopUserRead(
        user_id=user.id,
        first_name=user.first_name,
        birthdate=user.birthdate,
        gender=user.gender,
        about=user.about,
        telegram_username=user.telegram_username,
        instagram_username=user.instagram_username,
        photos=photos,
        created_at=user.created_at,
        likes_count=likes_count,
    )
