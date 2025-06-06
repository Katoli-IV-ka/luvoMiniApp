from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# -------------------------------
# 1) Общая базовая схема (UserBase)
# -------------------------------
class UserBase(BaseModel):
    telegram_user_id: int = Field(..., description="ID пользователя из Telegram")


# -------------------------------
# 2) Схема для создания (без is_premium и created_at)
#    (используется при первом логине: telegram_user_id приходит из WebApp)
# -------------------------------
class UserCreate(UserBase):
    pass
    # Поскольку при создании записи мы уже получаем `telegram_user_id`
    # из запроса (initData), других полей на этапе создания нам не нужно.
    # is_premium по умолчанию = False, premium_expires_at (None).


# -------------------------------
# 3) Схема для чтения (ч/з API) — UserRead
# -------------------------------
class UserRead(UserBase):
    id: int = Field(..., description="PK в базе данных")
    is_premium: bool = Field(..., description="Признак премиума")
    premium_expires_at: Optional[datetime] = Field(
        None, description="Дата окончания подписки (если премиум)"
    )
    created_at: datetime = Field(..., description="Дата и время создания аккаунта")

    class Config:
        orm_mode = True
        # Чтобы Pydantic понимал, что передаётся SQLAlchemy-модель.


# -------------------------------
# 4) Схема для обновления (UserUpdate)
# -------------------------------
class UserUpdate(BaseModel):
    # Позволяет клиенту обновить (например) статус премиума вручную (если нужна админка)
    is_premium: Optional[bool] = Field(None, description="Признак премиума")
    premium_expires_at: Optional[datetime] = Field(
        None, description="Дата окончания премиума"
    )

    class Config:
        orm_mode = True
