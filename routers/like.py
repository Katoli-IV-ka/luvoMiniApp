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
from schemas.like import LikeResponse
from schemas.profile import ProfileRead, TopProfileRead
from utils.s3 import build_photo_urls

router = APIRouter(prefix="", tags=["Likes"])


@router.post(
    "/like/{user_id}",
    response_model=LikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Поставить лайк и узнать, образовался ли матч",
)
async def like_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LikeResponse:
    # 1) Нельзя лайкать себя
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot like yourself")

    # 2) Проверяем профиль цели
    res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    target_profile = res.scalar_one_or_none()
    if not target_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 3) Сохраняем лайк, если его ещё нет
    exists = await db.execute(
        select(LikeModel).where(
            LikeModel.liker_id == current_user.id,
            LikeModel.liked_id == user_id,
        )
    )
    if not exists.scalar_one_or_none():
        new_like = LikeModel(liker_id=current_user.id, liked_id=user_id)
        db.add(new_like)
        await db.commit()
        await db.refresh(new_like)

    # 4) Проверяем взаимный лайк
    rec = await db.execute(
        select(LikeModel).where(
            LikeModel.liker_id == user_id,
            LikeModel.liked_id == current_user.id,
        )
    )
    if rec.scalar_one_or_none():
        # создаём матч, если ещё нет
        u1, u2 = sorted([current_user.id, user_id])
        m = await db.execute(
            select(MatchModel).where(
                MatchModel.user1_id == u1,
                MatchModel.user2_id == u2,
            )
        )
        if not m.scalar_one_or_none():
            new_match = MatchModel(user1_id=u1, user2_id=u2)
            db.add(new_match)
            await db.commit()
            await db.refresh(new_match)

        # собираем данные для ответа
        urls = await build_photo_urls(target_profile.user_id, db)
        profile_read = ProfileRead(
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
        return LikeResponse(matched=True, match_profile=profile_read)

    # 5) Нет взаимки
    return LikeResponse(matched=False)


@router.post(
    "/ignore/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отклонить входящий лайк (дизлайк)",
)
async def ignore_like(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LikeModel).where(
LikeModel.liker_id == user_id,
            LikeModel.liked_id == current_user.id,
        )
    )
    likes = result.scalars().all()

    if not likes:
        raise HTTPException(status_code=400, detail="Этот пользователь не ставил вам лайк")

    for like in likes:
        like.is_ignored = True
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
        select(LikeModel.liker_id)
        .where(LikeModel.liked_id == current_user.id)
    )
    liker_ids = [row[0] for row in res.all()]
    if not liker_ids:
        return []

    # 2) user_id всех, с кем уже есть матч
    res = await db.execute(
        select(MatchModel.user1_id)
        .where(MatchModel.user2_id == current_user.id)
    )
    ids1 = [row[0] for row in res.all()]
    res = await db.execute(
        select(MatchModel.user2_id)
        .where(MatchModel.user1_id == current_user.id)
    )
    ids2 = [row[0] for row in res.all()]
    matched_ids = set(ids1 + ids2)

    # 3) user_id всех, кого я проигнорировал
    res = await db.execute(
        select(LikeModel.liker_id)
        .where(LikeModel.liked_id == current_user.id, LikeModel.is_ignored == True)
    )
    ignored_ids = {row[0] for row in res.all()}

    # 4) Фильтрация кандидатов
    candidate_ids = [
        uid for uid in liker_ids
        if uid not in matched_ids and uid not in ignored_ids
    ]
    if not candidate_ids:
        return []

    # 5) Грузим профили по user_id
    res = await db.execute(
        select(Profile).where(Profile.user_id.in_(candidate_ids))
    )
    profiles = res.scalars().all()

    # 6) Формируем ответ
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
    response_model=List[TopProfileRead],
    summary="Топ-100 пользователей по числу полученных лайков",
)
async def top_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TopProfileRead]:
    # 1) Считаем количество лайков, сгруппированных по user_id
    likes_count_subq = (
        select(
            LikeModel.liked_id.label("user_id"),  # изменили на user_id
            func.count(LikeModel.id).label("likes_count")
        )
        .group_by(LikeModel.liked_id)
        .order_by(desc("likes_count"))
        .limit(100)
        .subquery()
    )

    # 2) Получаем профили и количество лайков для каждого профиля
    stmt = (
        select(
            Profile,
            likes_count_subq.c.likes_count
        )
        .join(likes_count_subq, Profile.user_id == likes_count_subq.c.user_id)  # соединяем по user_id
        .order_by(desc(likes_count_subq.c.likes_count))
    )
    res = await db.execute(stmt)
    rows = res.all()
    if not rows:
        return []

    # 3) Формируем список объектов для ответа
    output: List[TopProfileRead] = []
    for profile, likes_count in rows:
        # Ищем фото для каждого профиля
        urls = await build_photo_urls(profile.user_id, db)  # передаем user_id для поиска фото
        output.append(
            TopProfileRead(
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
                likes_count=likes_count,
            )
        )

    return output
