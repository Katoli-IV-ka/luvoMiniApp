# backend/schemas/instagram.py
from pydantic import BaseModel
from typing import List, Optional

class InstagramDataCreate(BaseModel):
    ig_username: str
    subscriptions: Optional[List[str]] = []

    class Config:
        orm_mode = True


class InstagramDataRead(BaseModel):
    user_id: int
    ig_username: str
    subscriptions: List[str]

    class Config:
        orm_mode = True
