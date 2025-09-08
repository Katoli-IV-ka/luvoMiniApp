from pydantic import BaseModel

from .user import UserRead


class BattlePair(BaseModel):
    user: UserRead
    opponent: UserRead

    class Config:
        from_attributes = True
        validate_by_name = True
