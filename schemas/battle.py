from datetime import datetime

from pydantic import BaseModel, Field

from .user import UserRead


class BattleRead(BaseModel):
    id: int = Field(..., description="ID баттла")
    user: UserRead
    opponent: UserRead
    created_at: datetime

    class Config:
        from_attributes = True
        validate_by_name = True
