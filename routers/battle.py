from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.battle import BattleSession
from models.user import User
from schemas.battle import BattleStage
from schemas.user import UserRead
from utils.user_helpers import to_user_read

router = APIRouter(prefix="/battle", tags=["battle"])


@router.get(
    "/pair",
    response_model=BattleStage,
    summary="Получить пару профилей для баттла",
)
async def get_battle_pair(
    winner_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BattleStage:
    today = datetime.now(timezone.utc).date()

    battle_session = await _get_today_session(db, current_user.id, today)

    if battle_session and battle_session.completed_rounds >= 15:
        return await _handle_completed_battle(
            db, battle_session, winner_id=winner_id
        )

    if winner_id is None:
        if battle_session is None:
            users = await _get_initial_pair(db, current_user)
            if len(users) < 2:
                raise HTTPException(status_code=404, detail="Недостаточно пользователей")

            battle_session = BattleSession(
                owner_id=current_user.id,
                battle_date=today,
                left_profile_id=users[0].id,
                right_profile_id=users[1].id,
            )
            db.add(battle_session)
            await db.commit()
            await db.refresh(battle_session)

        return await _build_stage_response(db, battle_session)

    if battle_session is None:
        raise HTTPException(status_code=400, detail="Баттл ещё не начат")

    winner_position = _get_winner_position(battle_session, winner_id)
    if winner_position is None:
        raise HTTPException(status_code=400, detail="Некорректный победитель")

    battle_session.completed_rounds += 1

    if battle_session.completed_rounds >= 15:
        battle_session.final_winner_id = winner_id
        battle_session.left_profile_id = None
        battle_session.right_profile_id = None
        await db.commit()
        await db.refresh(battle_session)
        return await _build_stage_response(db, battle_session)

    opponent = await _get_next_opponent(
        db,
        current_user,
        exclude_ids={current_user.id, winner_id},
    )
    if opponent is None:
        battle_session.completed_rounds -= 1
        await db.rollback()
        raise HTTPException(status_code=404, detail="Нет доступных соперников")

    if winner_position == 0:
        battle_session.left_profile_id = winner_id
        battle_session.right_profile_id = opponent.id
    else:
        battle_session.left_profile_id = opponent.id
        battle_session.right_profile_id = winner_id

    await db.commit()
    await db.refresh(battle_session)
    return await _build_stage_response(db, battle_session)


async def _get_today_session(
    db: AsyncSession, user_id: int, today: date
) -> BattleSession | None:
    stmt = (
        select(BattleSession)
        .where(
            BattleSession.owner_id == user_id,
            BattleSession.battle_date == today,
        )
        .order_by(BattleSession.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _handle_completed_battle(
    db: AsyncSession,
    battle_session: BattleSession,
    *,
    winner_id: int | None,
) -> BattleStage:
    if battle_session.final_winner_id is None and winner_id is not None:
        battle_session.final_winner_id = winner_id
        battle_session.left_profile_id = None
        battle_session.right_profile_id = None
        await db.commit()
        await db.refresh(battle_session)

    return await _build_stage_response(db, battle_session)


async def _build_stage_response(
    db: AsyncSession, battle_session: BattleSession
) -> BattleStage:
    if battle_session.final_winner_id is not None:
        winner = await db.get(User, battle_session.final_winner_id)
        if winner is None:
            raise HTTPException(status_code=404, detail="Победитель недоступен")
        winner_read = await to_user_read(winner, db)
        return BattleStage(
            stage=15,
            profiles=[],
            final_winner=winner_read,
            updated_at=battle_session.updated_at,
        )

    profiles: list[UserRead] = []

    if battle_session.left_profile_id is not None:
        left_user = await db.get(User, battle_session.left_profile_id)
        if left_user is None:
            raise HTTPException(status_code=404, detail="Профиль недоступен")
        profiles.append(await to_user_read(left_user, db))

    if battle_session.right_profile_id is not None:
        right_user = await db.get(User, battle_session.right_profile_id)
        if right_user is None:
            raise HTTPException(status_code=404, detail="Профиль недоступен")
        profiles.append(await to_user_read(right_user, db))

    if len(profiles) < 2 and battle_session.completed_rounds < 15:
        raise HTTPException(status_code=404, detail="Недостаточно пользователей")

    stage_number = min(battle_session.completed_rounds + 1, 15)
    return BattleStage(
        stage=stage_number,
        profiles=profiles,
        final_winner=None,
        updated_at=battle_session.updated_at,
    )


def _get_winner_position(
    battle_session: BattleSession, winner_id: int
) -> int | None:
    if battle_session.left_profile_id == winner_id:
        return 0
    if battle_session.right_profile_id == winner_id:
        return 1
    return None


async def _get_initial_pair(
    db: AsyncSession, current_user: User
) -> list[User]:
    stmt = select(User).where(User.id != current_user.id)
    stmt = _apply_gender_filter(stmt, current_user)
    stmt = stmt.order_by(func.random()).limit(2)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_next_opponent(
    db: AsyncSession,
    current_user: User,
    *,
    exclude_ids: set[int],
) -> User | None:
    stmt = select(User)
    if exclude_ids:
        stmt = stmt.where(~User.id.in_(tuple(exclude_ids)))
    stmt = _apply_gender_filter(stmt, current_user)
    stmt = stmt.order_by(func.random()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _apply_gender_filter(stmt, current_user: User):
    if current_user.gender == "male":
        stmt = stmt.where(User.gender == "female")
    elif current_user.gender == "female":
        stmt = stmt.where(User.gender == "male")
    return stmt
