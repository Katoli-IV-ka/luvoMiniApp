# backend/schemas/profile.py
from typing import Optional, List
from datetime import date, datetime

from pydantic import BaseModel, Field

# -------------------------------
# 1) Базовая схема (ProfileBase)
# -------------------------------
class ProfileBase(BaseModel):
    first_name: str = Field(..., max_length=100, description="Имя пользователя")
    birthdate: Optional[date] = Field(None, description="Дата рождения (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, max_length=10, description="Пол: 'male', 'female', 'other'")
    about: Optional[str] = Field(None, description="О себе (текстовое описание)")
    # Можно добавить latitude, longitude, когда будет геолокация:
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# -------------------------------
# 2) Схема для создания (Onboarding)
# -------------------------------
class ProfileCreate(ProfileBase):
    telegram_username: str = Field(..., max_length=64, description="Telegram username")
    instagram_username: Optional[str] = Field(None, max_length=64, description="Instagram username")


# -------------------------------
# 3) Схема для чтения (Response)
# -------------------------------
class ProfileRead(ProfileBase):
    id: int
    user_id: int
    telegram_username: str
    instagram_username: Optional[str]
    photos: List[str] = Field(..., description="Список URL фотографий профиля")
    created_at: datetime

    class Config:
        orm_mode = True


# -------------------------------
# 4) Схема для обновления (ProfileUpdate)
# -------------------------------
class ProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    birthdate: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=10)
    about: Optional[str] = None
    instagram_username: Optional[str] = Field(None, max_length=64)
    telegram_username: Optional[str] = Field(None, max_length=64)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        orm_mode = True