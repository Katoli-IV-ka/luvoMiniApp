from datetime import datetime

from pydantic import BaseModel

from .user import UserRead


class BattleStage(BaseModel):
    stage: int
    profiles: list[UserRead]
    final_winner: UserRead | None = None
    updated_at: datetime

    class Config:
        from_attributes = True
        validate_by_name = True
