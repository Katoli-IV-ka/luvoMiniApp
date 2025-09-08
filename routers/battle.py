from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, not_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.battle import Battle
from models.user import User
from models.like import Like as LikeModel
from models.match import Match as MatchModel
from schemas.battle import BattleRead, BattleVote
from routers.interactions import like_user

router = APIRouter(prefix="/battle", tags=["battle"])


@router.get("/start", response_model=BattleRead, summary="Начать баттл")
async def start_battle(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattleRead:
    sub_liked = select(LikeModel.liked_id).where(LikeModel.liker_id == current_user.id)
    sub_matched1 = select(MatchModel.user1_id).where(MatchModel.user2_id == current_user.id)
    sub_matched2 = select(MatchModel.user2_id).where(MatchModel.user1_id == current_user.id)
    stmt = select(User).where(
        User.id != current_user.id,
        not_(User.id.in_(sub_liked)),
        not_(User.id.in_(sub_matched1)),
        not_(User.id.in_(sub_matched2)),
    ).order_by(User.created_at.desc()).limit(1)

    if current_user.gender == "male":
        stmt = stmt.where(User.gender == "female")
    elif current_user.gender == "female":
        stmt = stmt.where(User.gender == "male")

    result = await db.execute(stmt)
    opponent = result.scalar_one_or_none()
    if not opponent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет доступных соперников")

    battle = Battle(user_id=current_user.id, opponent_id=opponent.id)
    db.add(battle)
    await db.commit()
    await db.refresh(battle)
    return battle


@router.post("/vote", response_model=BattleRead, summary="Проголосовать в баттле")
async def vote_battle(
    vote: BattleVote,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattleRead:
    battle = await db.get(Battle, vote.battle_id)
    if not battle or battle.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Баттл не найден")
    if battle.winner_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Голос уже был отдан")
    if vote.winner_id not in (battle.user_id, battle.opponent_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный winner_id")

    battle.winner_id = vote.winner_id
    await db.commit()
    await db.refresh(battle)

    if vote.winner_id == battle.opponent_id:
        await like_user(battle.opponent_id, db, current_user)

    return battle


@router.get("/history", response_model=List[BattleRead], summary="История баттлов")
async def battle_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[BattleRead]:
    stmt = select(Battle).where(
        or_(Battle.user_id == current_user.id, Battle.opponent_id == current_user.id)
    ).order_by(Battle.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
