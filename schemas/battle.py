from pydantic import BaseModel

from .user import UserRead


class BattleStage(BaseModel):
    stage: int
    profiles: list[UserRead]

    class Config:
        from_attributes = True
        validate_by_name = True
