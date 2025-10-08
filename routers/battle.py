from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.battle import BattlePair
from utils.user_helpers import to_user_read

router = APIRouter(prefix="/battle", tags=["battle"])


@router.get("/pair", response_model=BattlePair, summary="Получить пару профилей для баттла")
async def get_battle_pair(
    winner_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattlePair:
    if winner_id is not None:
        winner = await db.get(User, winner_id)
        if winner is None:
            raise HTTPException(status_code=404, detail="Победитель не найден")

        stmt = select(User).where(User.id != winner_id, User.id != current_user.id)
        if current_user.gender == "male":
            stmt = stmt.where(User.gender == "female")
        elif current_user.gender == "female":
            stmt = stmt.where(User.gender == "male")
        stmt = stmt.order_by(func.random()).limit(1)

        result = await db.execute(stmt)
        opponent = result.scalar_one_or_none()
        if opponent is None:
            raise HTTPException(status_code=404, detail="Нет доступных соперников")

        user_read = await to_user_read(winner, db)
        opponent_read = await to_user_read(opponent, db)
        return BattlePair(user=user_read, opponent=opponent_read)

    stmt = select(User).where(User.id != current_user.id)
    if current_user.gender == "male":
        stmt = stmt.where(User.gender == "female")
    elif current_user.gender == "female":
        stmt = stmt.where(User.gender == "male")
    stmt = stmt.order_by(func.random()).limit(2)

    result = await db.execute(stmt)
    users = result.scalars().all()
    if len(users) < 2:
        raise HTTPException(status_code=404, detail="Недостаточно пользователей")

    user_read = await to_user_read(users[0], db)
    opponent_read = await to_user_read(users[1], db)
    return BattlePair(user=user_read, opponent=opponent_read)
