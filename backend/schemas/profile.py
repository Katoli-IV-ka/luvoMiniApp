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
    # Можно добавить latitude, longitude, когда будем внедрять геолокацию:
    latitude: Optional[float] = Field(None, description="Широта пользователя")
    longitude: Optional[float] = Field(None, description="Долгота пользователя")


# -------------------------------
# 2) Схема для создания профиля (ProfileCreate)
#    (при создании указываем user_id + данные из ProfileBase)
# -------------------------------
class ProfileCreate(ProfileBase):
    # user_id приходит из токена (payload),
    # поэтому лучше его не передавать в теле запроса,
    # а извлекать на сервере из авторизационного токена.
    # Но если потребуется, можно раскомментировать:
    # user_id: int = Field(..., description="ID пользователя (из token)")
    pass


# -------------------------------
# 3) Схема для чтения профиля (ProfileRead)
# -------------------------------
class ProfileRead(ProfileBase):
    id: int = Field(..., description="PK профиля")
    user_id: int = Field(..., description="ID пользователя (из таблицы users)")
    created_at: datetime = Field(..., description="Дата и время создания профиля")

    # Схемы всех фото, если потребуется возвращать список их URL или ключей:
    #photos: Optional[List[str]] = Field(
    #    None, description="Список s3_key загруженных фото"
    #)

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        orm_mode = True
