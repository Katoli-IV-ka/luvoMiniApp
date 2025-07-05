from typing import Optional
from pydantic import BaseModel
from schemas.user import UserRead


class LikeResponse(BaseModel):
    matched: bool
    match_user: Optional[UserRead] = None

    class Config:
        from_attributes = True
        validate_by_name = True