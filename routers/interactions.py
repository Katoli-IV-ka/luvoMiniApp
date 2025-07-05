from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_

from core.database import get_db
from core.security import get_current_user
from models.feed_view import FeedView
from models.user import User
from models.like import Like as LikeModel
from models.match import Match as MatchModel
from schemas.like import LikeResponse
from schemas.user import UserRead, TopUserRead
from utils.s3 import build_photo_urls


router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post(
    "/view/{user_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Записать просмотр"
)
async def view_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя просматривать свой профиль")
    # Записываем просмотр
    view = FeedView(viewer_id=current_user.id, viewed_id=user_id)
    db.add(view)
    await db.commit()

    return


@router.post(
    "/like/{user_id}",
    response_model=LikeResponse,
    summary="Поставить лайк"
)
async def like_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LikeResponse:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя лайкать себя")

    # 1) Добавляем лайк, если его не было
    existing = await db.execute(
        select(func.count(LikeModel.id))
        .where(
            LikeModel.liker_id == current_user.id,
            LikeModel.liked_id == user_id,
        )
    )
    if existing.scalar_one() == 0:
        new_like = LikeModel(liker_id=current_user.id, liked_id=user_id)
        db.add(new_like)
        await db.commit()
        await db.refresh(new_like)

    # 2) Проверяем взаимный лайк
    mutual = await db.execute(
        select(func.count(LikeModel.id))
        .where(
            LikeModel.liker_id == user_id,
            LikeModel.liked_id == current_user.id,
        )
    )
    if mutual.scalar_one() > 0:
        # создаем матч при необходимости
        u1, u2 = sorted([current_user.id, user_id])
        match_check = await db.execute(
            select(func.count(MatchModel.id))
            .where(
                MatchModel.user1_id == u1,
                MatchModel.user2_id == u2,
            )
        )
        if match_check.scalar_one() == 0:
            new_match = MatchModel(user1_id=u1, user2_id=u2)
            db.add(new_match)
            await db.commit()
            await db.refresh(new_match)

        # возвращаем информацию о пользователе для матча
        matched = await db.get(User, user_id)
        if not matched:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        urls = await build_photo_urls(matched.id, db)
        user_read = UserRead(
            user_id=matched.id,
            telegram_user_id=matched.telegram_user_id,
            first_name=matched.first_name,
            birthdate=matched.birthdate,
            gender=matched.gender,
            about=matched.about,
            latitude=matched.latitude,
            longitude=matched.longitude,
            telegram_username=matched.telegram_username,
            instagram_username=matched.instagram_username,
            is_premium=matched.is_premium,
            premium_expires_at=matched.premium_expires_at,
            created_at=matched.created_at,
            photos=urls,
        )
        return LikeResponse(matched=True, match_user=user_read)

    return LikeResponse(matched=False, match_user=None)


@router.post(
    "/ignore/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отклонить входящий лайк (дизлайк)"
)
async def ignore_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя игнорировать себя")

    res = await db.execute(
        select(LikeModel)
        .where(
            LikeModel.liker_id == user_id,
            LikeModel.liked_id == current_user.id,
        )
    )
    like_obj = res.scalar_one_or_none()
    if not like_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")

    like_obj.is_ignored = True
    db.add(like_obj)
    await db.commit()
    return

@router.get(
    "/likes",
    response_model=List[UserRead],
    summary="Список пользователей, которые поставили вам лайк, без отклонённых и без матчей"
)
async def incoming_likes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[UserRead]:
    res = await db.execute(
        select(LikeModel.liker_id)
        .where(
            LikeModel.liked_id == current_user.id,
            LikeModel.is_ignored.is_(False),
        )
    )
    liker_ids = [row[0] for row in res.all()]
    if not liker_ids:
        return []

    # исключаем уже заматченных
    r1 = await db.execute(
        select(MatchModel.user1_id).where(MatchModel.user2_id == current_user.id)
    )
    r2 = await db.execute(
        select(MatchModel.user2_id).where(MatchModel.user1_id == current_user.id)
    )
    matched = set([r[0] for r in r1.all()] + [r[0] for r in r2.all()])

    output: List[UserRead] = []
    for uid in liker_ids:
        if uid in matched:
            continue
        user = await db.get(User, uid)
        if not user or not user.first_name:
            continue
        urls = await build_photo_urls(uid, db)
        output.append(UserRead(
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
            photos=urls,
        ))
    return output


@router.get(
    "/top",
    response_model=List[TopUserRead],
    summary="Топ пользователей по количеству лайков"
)
async def top_liked_users(
    db: AsyncSession = Depends(get_db),
) -> List[TopUserRead]:
    res = await db.execute(
        select(User, func.count(LikeModel.id).label("likes_count"))
        .join(LikeModel, LikeModel.liked_id == User.id)
        .group_by(User.id)
        .order_by(desc("likes_count"))
        .limit(20)
    )
    rows = res.all()
    output: List[TopUserRead] = []
    for user, likes_count in rows:
        urls = await build_photo_urls(user.id, db)
        output.append(TopUserRead(
            user_id=user.id,
            first_name=user.first_name,
            birthdate=user.birthdate,
            gender=user.gender,
            about=user.about,
            telegram_username=user.telegram_username,
            instagram_username=user.instagram_username,
            photos=urls,
            created_at=user.created_at,
            likes_count=likes_count,
        ))
    return output


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