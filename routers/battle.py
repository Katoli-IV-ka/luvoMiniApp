from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.battle_result import BattleResult
from schemas.user import UserRead
from schemas.battle import (
    BattlePairResponse,
    BattleVoteRequest,
    BattleVoteResponse,
    BattleRatingResponse,
    BattleLeaderboardItem,
)
from utils.s3 import build_photo_urls

router = APIRouter(prefix="/battle", tags=["battle"])


async def _user_to_read(user: User, db: AsyncSession) -> UserRead:
    photos = await build_photo_urls(user.id, db)
    return UserRead(
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
    )


@router.get("/pair", response_model=BattlePairResponse)
async def get_pair(
    winner_id: int | None = Query(None, description="ID победителя, если он остаётся"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattlePairResponse:
    if winner_id:
        winner = await db.get(User, winner_id)
        if not winner:
            raise HTTPException(status_code=404, detail="Winner not found")
        stmt = (
            select(User)
            .where(User.id.notin_([current_user.id, winner_id]))
            .order_by(func.random())
            .limit(1)
        )
        res = await db.execute(stmt)
        opponent = res.scalar_one_or_none()
        if not opponent:
            raise HTTPException(status_code=404, detail="No opponent found")
        return BattlePairResponse(
            left=await _user_to_read(winner, db),
            right=await _user_to_read(opponent, db),
        )
    else:
        stmt = (
            select(User)
            .where(User.id != current_user.id)
            .order_by(func.random())
            .limit(2)
        )
        res = await db.execute(stmt)
        users = res.scalars().all()
        if len(users) < 2:
            raise HTTPException(status_code=404, detail="Not enough users")
        return BattlePairResponse(
            left=await _user_to_read(users[0], db),
            right=await _user_to_read(users[1], db),
        )


@router.post("/vote", response_model=BattleVoteResponse)
async def vote(
    payload: BattleVoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattleVoteResponse:
    winner = await db.get(User, payload.winner_id)
    loser = await db.get(User, payload.loser_id)
    if not winner or not loser:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(BattleResult(winner_id=winner.id, loser_id=loser.id))
    winner.battle_wins += 1
    winner.battle_rating += 1
    loser.battle_losses += 1
    await db.commit()

    stmt = (
        select(User)
        .where(User.id.notin_([current_user.id, winner.id, loser.id]))
        .order_by(func.random())
        .limit(1)
    )
    res = await db.execute(stmt)
    opponent = res.scalar_one_or_none()
    if not opponent:
        raise HTTPException(status_code=404, detail="No opponent found")

    return BattleVoteResponse(
        winner=await _user_to_read(winner, db),
        opponent=await _user_to_read(opponent, db),
    )


@router.get("/rating/{user_id}", response_model=BattleRatingResponse)
async def get_rating(user_id: int, db: AsyncSession = Depends(get_db)) -> BattleRatingResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return BattleRatingResponse(
        wins=user.battle_wins,
        losses=user.battle_losses,
        score=user.battle_rating,
    )


@router.get("/leaderboard", response_model=List[BattleLeaderboardItem])
async def leaderboard(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[BattleLeaderboardItem]:
    stmt = (
        select(User)
        .order_by(User.battle_rating.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [
        BattleLeaderboardItem(
            user_id=u.id,
            first_name=u.first_name,
            score=u.battle_rating,
        )
        for u in users
    ]

