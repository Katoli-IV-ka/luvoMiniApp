# routers/like.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.profile import Profile
from models.like import Like as LikeModel
from models.match import Match as MatchModel
from models.feed_view import FeedView
from schemas.like import LikeResponse

from schemas.profile import ProfileRead
from utils.s3 import build_photo_urls

router = APIRouter(prefix="", tags=["Likes"])


@router.post(
    "/like/{profile_id}",
    response_model=LikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Поставить лайк и узнать, образовался ли матч",
)
async def like_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LikeResponse:
    if profile_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot like yourself")


    # 1) Находим профиль и получаем user_id
    res = await db.execute(select(Profile).where(Profile.id == profile_id))


    target_profile = res.scalar_one_or_none()
    if not target_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    target_user_id = target_profile.user_id

    # 2) Сохраняем лайк, если его ещё нет
    existing = await db.execute(
        select(LikeModel).where(
            LikeModel.liker_id == current_user.id,
            LikeModel.liked_id == target_user_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(LikeModel(liker_id=current_user.id, liked_id=target_user_id))
        await db.commit()

    # 3) Проверяем взаимный лайк
    reciprocal = await db.execute(
        select(LikeModel).where(
            LikeModel.liker_id == target_user_id,
            LikeModel.liked_id == current_user.id,
        )
    )
    if reciprocal.scalar_one_or_none():
        # создаём Match, если нужно
        user1, user2 = sorted([current_user.id, target_user_id])
        matched = await db.execute(
            select(MatchModel).where(
                MatchModel.user1_id == user1,
                MatchModel.user2_id == user2,
            )
        )
        if not matched.scalar_one_or_none():
            db.add(MatchModel(user1_id=user1, user2_id=user2))
            await db.commit()

        # возвращаем данные профиля матча
        urls = await build_photo_urls(target_user_id, db)
        match_profile = ProfileRead(
            id=target_profile.id,
            user_id=target_user_id,
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

    return LikeResponse(matched=False)


@router.post(
    "/ignore/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отклонить входящий лайк (дизлайк)",
)
async def ignore_like(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) Находим профиль и получаем user_id
    res = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    target_user_id = profile.user_id

    # 2) Проверяем, что этот пользователь ставил вам лайк
    res = await db.execute(
        select(LikeModel).where(
            LikeModel.liker_id == target_user_id,
            LikeModel.liked_id == current_user.id,
        )
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Этот пользователь не ставил вам лайк")

    # 3) Проверяем, что матча ещё нет
    user1, user2 = sorted([current_user.id, target_user_id])
    res = await db.execute(
        select(MatchModel).where(
            MatchModel.user1_id == user1,
            MatchModel.user2_id == user2,
        )
    )
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Вы уже в матче с этим пользователем")

    # 4) Помечаем как просмотренного/отклонённого
    res = await db.execute(
        select(FeedView).where(
            FeedView.viewer_id == current_user.id,
            FeedView.viewed_id == target_user_id,
        )
    )
    if not res.scalar_one_or_none():
        db.add(FeedView(viewer_id=current_user.id, viewed_id=target_user_id))
        await db.commit()

    return

@router.get(
    "/likes",
    response_model=List[ProfileRead],
    summary="Список пользователей, которые поставили вам лайк, без отклонённых и без матчей",
)
async def incoming_likes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProfileRead]:

    # 1) Все user_id, кто лайкнул меня
    res = await db.execute(
        select(LikeModel.liker_id).where(LikeModel.liked_id == current_user.id)
    )
    liker_ids = [row[0] for row in res.all()]
    if not liker_ids:
        return []

    # 2) user_id всех, с кем уже есть матч
    res = await db.execute(
        select(MatchModel.user1_id).where(MatchModel.user2_id == current_user.id)
    )
    ids1 = [row[0] for row in res.all()]
    res = await db.execute(
        select(MatchModel.user2_id).where(MatchModel.user1_id == current_user.id)
    )
    ids2 = [row[0] for row in res.all()]
    matched_ids = set(ids1 + ids2)

    # 3) user_id всех, которых я отклонил
    res = await db.execute(
        select(FeedView.viewed_id).where(FeedView.viewer_id == current_user.id)
    )
    dismissed_ids = {row[0] for row in res.all()}

    # 4) Фильтрация
    candidate_ids = [
        uid for uid in liker_ids
        if uid not in matched_ids and uid not in dismissed_ids
    ]
    if not candidate_ids:
        return []

    res = await db.execute(
        select(Profile).where(Profile.user_id.in_(candidate_ids))
    )
    profiles = res.scalars().all()

    output: List[ProfileRead] = []
    for p in profiles:
        urls = await build_photo_urls(p.user_id, db)
        output.append(
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

    return output


@router.get(
    "/top",
    response_model=List[ProfileRead],
    summary="Топ-100 пользователей по числу полученных лайков",
)
async def top_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # чтобы только авторизованные могли смотреть
) -> List[ProfileRead]:
    # 1) Собираем top 100 user_id с наибольшим числом лайков
    likes_count_subq = (
        select(
            LikeModel.liked_id.label("user_id"),
            func.count(LikeModel.id).label("likes_count")
        )
        .group_by(LikeModel.liked_id)
        .order_by(desc("likes_count"))
        .limit(100)
        .subquery()
    )

    # 2) Джоиним с профилями
    stmt = (
        select(
            Profile,
            likes_count_subq.c.likes_count
        )
        .join(likes_count_subq, Profile.user_id == likes_count_subq.c.user_id)
        .order_by(desc(likes_count_subq.c.likes_count))
    )
    res = await db.execute(stmt)
    rows = res.all()
    if not rows:
        return []

    # 3) Формируем ответ
    output: List[ProfileRead] = []
    for profile, likes_count in rows:
        urls = await build_photo_urls(profile.user_id, db)
        output.append(
            ProfileRead(
                id=profile.id,
                user_id=profile.user_id,
                first_name=profile.first_name,
                birthdate=profile.birthdate,
                gender=profile.gender,
                about=profile.about,
                telegram_username=profile.telegram_username,
                instagram_username=profile.instagram_username,
                photos=urls,
                created_at=profile.created_at,
            )
        )

    return output