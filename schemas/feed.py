# backend/schemas/feed.py

from pydantic import BaseModel, Field


class ViewRequest(BaseModel):
    user_id: int = Field(..., alias="user_id", description="ID пользователя")

    class Config:
        validate_by_name = True
