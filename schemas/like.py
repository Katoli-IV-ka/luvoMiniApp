# backend/schemas/like.py
from datetime import datetime
from pydantic import BaseModel


class LikeBase(BaseModel):
    liker_id: int
    liked_id: int


class LikeCreate(LikeBase):
    pass


class LikeRead(LikeBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
