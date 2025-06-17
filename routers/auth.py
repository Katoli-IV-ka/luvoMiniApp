# backend/routers/auth.py
import json

from fastapi import APIRouter

from schemas.auth import TokenResponse, InitDataSchema
from models.profile import Profile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.security import verify_init_data
from core.config import settings
from core.database import get_db
from models.user import User

from fastapi import Depends, HTTPException
from jose import jwt

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
    "/",
    response_model=TokenResponse,
    summary="Авторизация через Telegram WebApp initData → выдаёт JWT"
)
async def login(
    init_data: InitDataSchema,
    db: AsyncSession = Depends(get_db),
):
    # 1) валидируем подпись и парсим init_data
    data = verify_init_data(init_data.init_data)
    user_obj = data.get("user")
    if not user_obj:
        raise HTTPException(status_code=400, detail="Missing 'user' in init_data")
    user_data = json.loads(user_obj)
    tg_id = user_data.get("id")
    if not tg_id:
        raise HTTPException(status_code=400, detail="Invalid 'user' data in init_data")

    # 2) ищем или создаём User
    stmt = select(User).where(User.telegram_user_id == tg_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_user_id=tg_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 3) генерируем JWT
    token_payload = {"user_id": user.id}
    access_token = jwt.encode(token_payload, settings.TELEGRAM_BOT_TOKEN, algorithm="HS256")

    # 4) проверяем, есть ли профиль
    stmt_profile = select(Profile.id).where(Profile.user_id == user.id).limit(1)
    result_profile = await db.execute(stmt_profile)
    has_profile = result_profile.scalar_one_or_none() is not None

    # 5) возвращаем токен и флаг наличия профиля
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        has_profile=has_profile,
    )


