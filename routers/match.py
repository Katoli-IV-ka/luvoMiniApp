# backend/routers/match.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.match import Match as MatchModel
from schemas.user import UserRead
from utils.s3 import build_photo_urls

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get(
    "/",
    response_model=List[UserRead],
    summary="Список пользователей, с которыми у вас совпадения"
)
async def get_my_matches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[UserRead]:
    # Ищем все матчи, где текущий пользователь — участник
    stmt = select(MatchModel).where(
        or_(
            MatchModel.user1_id == current_user.id,
            MatchModel.user2_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    matches = result.scalars().all()

    out: List[UserRead] = []
    for match in matches:
        # Определяем ID другого пользователя в матче
        other_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
        user = await db.get(User, other_id)
        if not user or not user.first_name:
            continue

        photos = await build_photo_urls(other_id, db)
        out.append(UserRead(
            user_id=user.id,
            telegram_user_id=user.telegram_user_id,
            first_name=user.first_name,
            birthdate=user.birthdate,
            gender=user.gender,
            about=user.about,
            latitude=user.latitude,
            longitude=user.longitude,
            telegram_username=user.telegram_username,
            instagram_username=user.instagram_username,
            is_premium=user.is_premium,
            premium_expires_at=user.premium_expires_at,
            created_at=user.created_at,
            photos=photos,
        ))
    return out
