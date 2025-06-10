# backend/routers/feed.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import get_db
from models.profile import Profile
from models.instagram_data import InstagramData
from models.user import User
from models.like import Like
from models.match import Match
from schemas.profile import ProfileRead
from schemas.like import LikeCreate, LikeRead
from typing import List

router = APIRouter(prefix="/feed", tags=["feed"])

@router.get("/next", response_model=List[ProfileRead])
async def get_feed(
    telegram_user_id: int,  # в реальности будет из токена
    db: AsyncSession = Depends(get_db),
):
    # 1. Получаем информацию о текущем пользователе
    stmt_user = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt_user)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Получаем подписки пользователя из Instagram
    stmt_ig = select(InstagramData).where(InstagramData.user_id == user.id)
    instagram_data = (await db.execute(stmt_ig)).scalar_one_or_none()

    if instagram_data:
        # 3. Получаем пользователей, которых подписал текущий пользователь
        stmt_feed = (
            select(Profile)
            .join(User)
            .where(User.id.in_(instagram_data.matched_users))  # Подписки, которые зарегистрированы в системе
            .options(selectinload(Profile.photos))  # Подгружаем фотографии
            .limit(20)
        )
        profiles = (await db.execute(stmt_feed)).scalars().all()
    else:
        # Если Instagram не подключён, берём случайных пользователей
        stmt_feed = (
            select(Profile)
            .join(User)
            .where(User.telegram_user_id != telegram_user_id)  # исключаем себя
            .limit(20)
        )
        profiles = (await db.execute(stmt_feed)).scalars().all()

    # Формируем результат ленты
    return [
        ProfileRead(
            id=profile.id,
            user_id=profile.user_id,
            first_name=profile.first_name,
            birthdate=profile.birthdate,
            gender=profile.gender,
            about=profile.about,
            latitude=profile.latitude,
            longitude=profile.longitude,
            created_at=profile.created_at,
            photos=[photo.s3_key for photo in profile.photos]
        )
        for profile in profiles
    ]

@router.post("/like", response_model=LikeRead)
async def like_profile(
    like_in: LikeCreate,
    telegram_user_id: int,  # передаём в query параметры
    db: AsyncSession = Depends(get_db),
):
    # 1) Находим пользователя, который ставит лайк
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 2) Проверим, что лайк не был поставлен ранее
    stmt2 = select(Like).where(
        Like.liker_id == user.id, Like.liked_id == like_in.liked_id
    )
    existing_like = (await db.execute(stmt2)).scalar_one_or_none()

    if existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already liked")

    # 3) Создаём новый лайк
    new_like = Like(liker_id=user.id, liked_id=like_in.liked_id)
    db.add(new_like)
    await db.commit()
    await db.refresh(new_like)

    # 4) Проверим, есть ли взаимный лайк (матч)
    stmt3 = select(Like).where(
        Like.liker_id == like_in.liked_id, Like.liked_id == user.id
    )
    mutual_like = (await db.execute(stmt3)).scalar_one_or_none()

    if mutual_like:
        # Если есть взаимный лайк — создаём матч
        match = Match(user1_id=user.id, user2_id=like_in.liked_id)
        db.add(match)
        await db.commit()

    return new_like
