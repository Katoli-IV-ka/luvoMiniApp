# schemas/like.py
from typing import Optional
from pydantic import BaseModel
from .profile import ProfileRead

class LikeResponse(BaseModel):
    matched: bool
    match_profile: Optional[ProfileRead] = None

    class Config:
        from_attributes = True
