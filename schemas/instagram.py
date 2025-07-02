from pydantic import BaseModel
from typing import List
from datetime import datetime

class InstagramDataRead(BaseModel):
    user_id: int
    ig_username: str
    last_sync: datetime
    subscriptions: List[str]

    class Config:
        from_attributes = True