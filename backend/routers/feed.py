# backend/routers/feed.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.like import Like
from models.user import User
from schemas.like import LikeCreate, LikeRead
from models.match import Match

router = APIRouter(prefix="/feed", tags=["feed"])


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
