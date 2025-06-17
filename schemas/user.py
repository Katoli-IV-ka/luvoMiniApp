from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.profile import ProfileRead


class UserBase(BaseModel):
    telegram_user_id: int = Field(..., description="ID пользователя из Telegram")


class UserCreate(UserBase):
    pass
    # Поскольку при создании записи мы уже получаем `telegram_user_id`
    # из запроса (initData), других полей на этапе создания нам не нужно.
    # is_premium по умолчанию = False, premium_expires_at (None).


class UserRead(UserBase):
    id: int = Field(..., description="PK в базе данных")
    is_premium: bool = Field(..., description="Признак премиума")
    premium_expires_at: Optional[datetime] = Field(
        None, description="Дата окончания подписки (если премиум)"
    )
    created_at: datetime = Field(..., description="Дата и время создания аккаунта")
    profile: Optional[ProfileRead] = None

    class Config:
        from_attributes = True
        # Чтобы Pydantic понимал, что передаётся SQLAlchemy-модель.


class UserUpdate(BaseModel):
    # Позволяет клиенту обновить (например) статус премиума вручную (если нужна админка)
    is_premium: Optional[bool] = Field(None, description="Признак премиума")
    premium_expires_at: Optional[datetime] = Field(
        None, description="Дата окончания премиума"
    )

    class Config:
        from_attributes = True
