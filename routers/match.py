from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.profile import Profile
from models.match import Match as MatchModel
from schemas.profile import ProfileRead
from utils.s3 import build_photo_urls

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get(
    "/",
    response_model=List[ProfileRead],
    summary="Список профилей, с которыми у вас есть взаимный лайк (матчи)"
)
async def get_my_matches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProfileRead]:
    # 1) Собираем все matched user_id для текущего
    # те, где я — user1
    res1 = await db.execute(
        select(MatchModel.user2_id)
        .where(MatchModel.user1_id == current_user.id)
    )
    ids1 = [r[0] for r in res1.all()]

    # и где я — user2
    res2 = await db.execute(
        select(MatchModel.user1_id)
        .where(MatchModel.user2_id == current_user.id)
    )
    ids2 = [r[0] for r in res2.all()]

    matched_ids = ids1 + ids2
    if not matched_ids:
        return []

    # 2) Подтягиваем профили этих пользователей
    res = await db.execute(
        select(Profile).where(Profile.user_id.in_(matched_ids))
    )
    profiles = res.scalars().all()

    # 3) Формируем список ProfileRead
    out: List[ProfileRead] = []
    for p in profiles:
        urls = await build_photo_urls(p.user_id, db)
        out.append(
            ProfileRead(
                id=p.id,
                user_id=p.user_id,
                first_name=p.first_name,
                birthdate=p.birthdate,
                gender=p.gender,
                about=p.about,
                telegram_username=p.telegram_username,
                instagram_username=p.instagram_username,
                photos=urls,
                created_at=p.created_at,
            )
        )
    return out
