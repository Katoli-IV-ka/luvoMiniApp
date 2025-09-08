from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, not_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.battle import Battle
from models.user import User
from models.like import Like as LikeModel
from models.match import Match as MatchModel
from schemas.battle import BattleRead
from schemas.user import UserRead

router = APIRouter(prefix="/battle", tags=["battle"])


@router.get("/start", response_model=BattleRead, summary="Получить соперника для баттла")
async def start_battle(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattleRead:
    sub_liked = select(LikeModel.liked_id).where(LikeModel.liker_id == current_user.id)
    sub_matched1 = select(MatchModel.user1_id).where(MatchModel.user2_id == current_user.id)
    sub_matched2 = select(MatchModel.user2_id).where(MatchModel.user1_id == current_user.id)
    stmt = (
        select(User)
        .where(
            User.id != current_user.id,
            not_(User.id.in_(sub_liked)),
            not_(User.id.in_(sub_matched1)),
            not_(User.id.in_(sub_matched2)),
        )
        .order_by(User.created_at.desc())
        .limit(1)
    )

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

    return BattleRead(
        id=battle.id,
        user=UserRead.model_validate(current_user),
        opponent=UserRead.model_validate(opponent),
        created_at=battle.created_at,
    )
