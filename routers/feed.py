from typing import List, Set

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.instagram_connection import InstagramConnection

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
    # 1) Свой профиль
    res = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    my_profile = res.scalar_one_or_none()
    if not my_profile:
        raise HTTPException(status_code=401, detail="Your profile not found")

    # 2) Уже просмотренные user_id
    res = await db.execute(
        select(FeedView.viewed_id).where(FeedView.viewer_id == current_user.id)
    )
    viewed: Set[int] = {r[0] for r in res.all()}

    # 3) Первый уровень: подписки и подписчики
    res = await db.execute(
        select(InstagramConnection.connected_id)
        .where(
            InstagramConnection.user_id == current_user.id,
            InstagramConnection.type == "subscription"
        )
    )
    subs = {r[0] for r in res.all()}
    res = await db.execute(
        select(InstagramConnection.user_id)
        .where(
            InstagramConnection.connected_id == current_user.id,
            InstagramConnection.type == "subscription"
        )
    )
    followers = {r[0] for r in res.all()}
    lvl1 = (subs | followers) - {current_user.id} - viewed

    # 4) Второй уровень: подписки моих подписок
    res = await db.execute(
        select(InstagramConnection.connected_id)
        .where(
            InstagramConnection.user_id.in_(subs),
            InstagramConnection.type == "subscription"
        )
    )
    lvl2 = set(r[0] for r in res.all()) - lvl1 - {current_user.id} - viewed

    # 5) Все остальные
    res = await db.execute(
        select(Profile.user_id)
        .where(
            Profile.user_id != current_user.id,
            Profile.user_id.not_in(viewed | lvl1 | lvl2),
            Profile.gender != my_profile.gender
        )
    )
    others = [r[0] for r in res.all()]

    # 6) Собираем единый упорядоченный список и применяем skip/limit
    ordered = list(lvl1) + list(lvl2) + others
    page = ordered[skip: skip + limit]

    # 6.1) Если после всех уровней нет профилей — забираем случайных
    if not page:
        res = await db.execute(
            select(Profile)
            .where(
                Profile.user_id != current_user.id,
                Profile.gender != my_profile.gender,
            )
            .order_by(func.random())
            .limit(limit)
        )
        random_profiles = res.scalars().all()
        batch = []
        for p in random_profiles:
            urls = await build_photo_urls(p.user_id, db)
            batch.append(
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
        return batch

    # 7) Достаём Profile для этих user_id
    res = await db.execute(
        select(Profile).where(Profile.user_id.in_(page))
    )
    profiles = {p.user_id: p for p in res.scalars().all()}

    # 8) Формируем ответ в том же порядке
    batch: List[ProfileRead] = []
    for uid in page:
        p = profiles.get(uid)
        urls = await build_photo_urls(uid, db)
        batch.append(
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
    # 1) Проверка существования
    res = await db.execute(
        select(Profile).where(Profile.id == req.profile_id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) Запись в FeedView
    res = await db.execute(
        select(FeedView).where(
            FeedView.viewer_id == current_user.id,
            FeedView.viewed_id == profile.user_id
        )
    )
    if not res.scalar_one_or_none():
        db.add(FeedView(viewer_id=current_user.id, viewed_id=profile.user_id))
        await db.commit()
    return