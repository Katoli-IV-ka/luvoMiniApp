from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BattleCreate(BaseModel):
    opponent_id: int = Field(..., description="ID соперника")

    class Config:
        from_attributes = True
        validate_by_name = True


class BattleVote(BaseModel):
    battle_id: int = Field(..., description="ID баттла")
    winner_id: int = Field(..., description="ID победителя")

    class Config:
        from_attributes = True
        validate_by_name = True


class BattleRead(BaseModel):
    id: int
    user_id: int
    opponent_id: int
    winner_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
        validate_by_name = True
