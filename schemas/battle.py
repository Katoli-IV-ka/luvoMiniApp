# backend/schemas/battle.py
from typing import List
from pydantic import BaseModel, Field

from schemas.user import UserRead


class BattlePairResponse(BaseModel):
    left: UserRead
    right: UserRead

    class Config:
        from_attributes = True
        validate_by_name = True


class BattleVoteRequest(BaseModel):
    winner_id: int = Field(..., description="ID победителя")
    loser_id: int = Field(..., description="ID проигравшего")


class BattleVoteResponse(BaseModel):
    winner: UserRead
    opponent: UserRead

    class Config:
        from_attributes = True
        validate_by_name = True


class BattleRatingResponse(BaseModel):
    wins: int
    losses: int
    score: int

    class Config:
        from_attributes = True
        validate_by_name = True


class BattleLeaderboardItem(BaseModel):
    user_id: int
    first_name: str | None = None
    score: int

    class Config:
        from_attributes = True
        validate_by_name = True
