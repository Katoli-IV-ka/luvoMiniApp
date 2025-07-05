from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


class PhotoRead(BaseModel):
    photo_id: int = Field(..., alias="photo_id", description="PK в базе данных")
    user_id: int = Field(..., alias="user_id", description="ID пользователя")
    url: HttpUrl = Field(..., description="URL изображения")
    is_general: bool = Field(..., description="Признак главной фотографии")
    created_at: datetime = Field(..., description="Дата и время добавления фотографии")

    class Config:
        from_attributes = True
        validate_by_name = True
