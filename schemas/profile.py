# backend/schemas/profile.py
from typing import Optional, List
from datetime import date, datetime

from pydantic import BaseModel, Field


class ProfileBase(BaseModel):
    first_name: str = Field(..., max_length=100, description="Имя пользователя")
    birthdate: Optional[date] = Field(None, description="Дата рождения (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, max_length=10, description="Пол: 'male', 'female', 'other'")
    about: Optional[str] = Field(None, description="О себе (текстовое описание)")
    # Можно добавить latitude, longitude, когда будет геолокация:
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProfileCreate(ProfileBase):
    telegram_username: str = Field(..., max_length=64, description="Telegram username")
    instagram_username: Optional[str] = Field(None, max_length=64, description="Instagram username")


class ProfileRead(ProfileBase):
    id: int
    user_id: int
    telegram_username: str
    instagram_username: Optional[str]
    photos: List[str] = Field(..., description="Список URL фотографий профиля")
    created_at: datetime

    class Config:
        from_attributes = True


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
        from_attributes = True #orm_mode

class TopProfileRead(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str]
    birthdate: Optional[date]
    gender: Optional[str]
    about: Optional[str]
    telegram_username: Optional[str]
    instagram_username: Optional[str]
    photos: List[str]
    created_at: datetime
    likes_count: int