from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db

from models.user import User
from models.profile import Profile
from models.feed_view import FeedView
from core.security import get_current_user
from schemas.feed import ViewRequest
from schemas.profile import ProfileRead
from utils.s3 import build_photo_urls

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get(
    "/",
    response_model=List[ProfileRead],
    summary="Получить пачку профилей для ленты",
)
async def get_feed_batch(
    skip: int = Query(0, ge=0, description="Сколько профилей пропустить"),
    limit: int = Query(10, ge=1, le=50, description="Сколько профилей вернуть"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProfileRead]:
    # 1) Получаем свой профиль
    res = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    my_profile = res.scalar_one_or_none()
    if not my_profile:
        raise HTTPException(status_code=404, detail="Your profile not found")

    # 2) Собираем viewed_ids
    res = await db.execute(
        select(FeedView.viewed_id).where(FeedView.viewer_id == current_user.id)
    )

    viewed_ids = [r[0] for r in res.all()]

    # 3) Ищем пачку кандидатов
    stmt = (
        select(Profile)
        .where(
            Profile.user_id != current_user.id,
            Profile.gender != my_profile.gender,
            Profile.user_id.not_in(viewed_ids),
        )
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    candidates = res.scalars().all()

    # 4) Формируем список Pydantic-моделей с фото
    batch: List[ProfileRead] = []
    for cand in candidates:
        urls = await build_photo_urls(cand.user_id, db)
        batch.append(
            ProfileRead(
                id=cand.id,
                user_id=cand.user_id,
                first_name=cand.first_name,
                birthdate=cand.birthdate,
                gender=cand.gender,
                about=cand.about,
                telegram_username=cand.telegram_username,
                instagram_username=cand.instagram_username,
                photos=urls,
                created_at=cand.created_at,
            )
        )

    return batch


@router.post(
    "/view",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отметить просмотр профиля в ленте",
)
async def mark_view(
    req: ViewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) Проверяем, что профиль существует
    print(req.profile_id)
    res = await db.execute(
        select(Profile).where(Profile.id == req.profile_id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) Если ещё не было отметки просмотра — добавляем её
    res = await db.execute(
        select(FeedView).where(
            FeedView.viewer_id == current_user.id,
            FeedView.viewed_id == profile.user_id,
        )
    )
    if not res.scalar_one_or_none():
        db.add(FeedView(viewer_id=current_user.id, viewed_id=profile.user_id))
        await db.commit()

    return