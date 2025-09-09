from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from schemas.battle import BattlePair
from schemas.user import UserRead
from utils.s3 import build_photo_urls

router = APIRouter(prefix="/battle", tags=["battle"])


@router.get("/pair", response_model=BattlePair, summary="Получить пару профилей для баттла")
async def get_battle_pair(
    winner_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> BattlePair:
    if winner_id is not None:
        winner = await db.get(User, winner_id)
        if winner is None:
            raise HTTPException(status_code=404, detail="Победитель не найден")
        stmt = select(User).where(User.id != winner_id).order_by(func.random()).limit(1)
        result = await db.execute(stmt)
        opponent = result.scalar_one_or_none()
        if opponent is None:
            raise HTTPException(status_code=404, detail="Нет доступных соперников")
        return BattlePair(
            user=UserRead.model_validate(winner),
            opponent=UserRead.model_validate(opponent),
        )

    stmt = select(User).order_by(func.random()).limit(2)
    result = await db.execute(stmt)
    users = result.scalars().all()
    if len(users) < 2:
        raise HTTPException(status_code=404, detail="Недостаточно пользователей")

    user_read = await _to_user_read(users[0], db)
    opponent_read = await _to_user_read(users[1], db)
    return BattlePair(user=user_read, opponent=opponent_read)

async def _to_user_read(user: User, db: AsyncSession) -> UserRead:
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
