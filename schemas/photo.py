# schemas/photo.py

from pydantic import BaseModel, HttpUrl
from datetime import datetime

class PhotoRead(BaseModel):
    id: int
    profile_id: int
    url: HttpUrl
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True