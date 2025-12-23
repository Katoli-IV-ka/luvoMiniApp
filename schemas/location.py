from pydantic import BaseModel, Field


class LocationUpdate(BaseModel):
    country: str = Field(..., max_length=64, description="Страна пользователя")
    city: str = Field(..., max_length=64, description="Город пользователя")
    district: str = Field(..., max_length=128, description="Район пользователя")
