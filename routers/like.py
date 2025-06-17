# routers/like.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from core.database import get_db

from models.user    import User
from models.profile import Profile
from models.like    import Like as LikeModel
from models.match   import Match as MatchModel
from core.security import get_current_user
from schemas.like   import LikeResponse
from schemas.profile import ProfileRead
from utils.s3       import build_photo_urls

router = APIRouter(prefix="/like", tags=["like"])

@router.post(
    "/{profile_id}",
    response_model=LikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Поставить лайк и узнать, образовался ли матч",
)
async def like_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LikeResponse:
    # 1) Нельзя лайкать себя
    if profile_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot like yourself")

    # 2) Проверяем, что профиль существует
    res = await db.execute(select(Profile).where(Profile.user_id == profile_id))
    target_profile = res.scalar_one_or_none()
    if not target_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 3) Сохраняем лайк (если ещё не лайкано)
    existing = await db.execute(
        select(LikeModel)
        .where(
            LikeModel.liker_id == current_user.id,
            LikeModel.liked_id == profile_id
        )
    )
    if not existing.scalar_one_or_none():
        db.add(LikeModel(liker_id=current_user.id, liked_id=profile_id))
        await db.commit()

    # 4) Проверяем взаимный лайк
    reciprocal = await db.execute(
        select(LikeModel)
        .where(
            LikeModel.liker_id == profile_id,
            LikeModel.liked_id == current_user.id
        )
    )
    if reciprocal.scalar_one_or_none():
        # Матч!
        # Проверяем, не создавали ли уже запись в Match
        user1, user2 = sorted([current_user.id, profile_id])
        existing_match = await db.execute(
            select(MatchModel)
            .where(
                MatchModel.user1_id == user1,
                MatchModel.user2_id == user2
            )
        )
        if not existing_match.scalar_one_or_none():
            db.add(MatchModel(user1_id=user1, user2_id=user2))
            await db.commit()

        # Формируем данные профиля для уведомления
        urls = await build_photo_urls(profile_id, db)
        match_profile = ProfileRead(
            id=target_profile.id,
            user_id=target_profile.user_id,
            first_name=target_profile.first_name,
            birthdate=target_profile.birthdate,
            gender=target_profile.gender,
            about=target_profile.about,
            telegram_username=target_profile.telegram_username,
            instagram_username=target_profile.instagram_username,
            photos=urls,
            created_at=target_profile.created_at,
        )
        return LikeResponse(matched=True, match_profile=match_profile)

    # 5) Нет совпадения
    return LikeResponse(matched=False)
