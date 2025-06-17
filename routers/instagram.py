# routers/instagram.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.profile import Profile

from models.user import User
from core.auth import get_current_user
from schemas.instagram import InstagramDataRead
from services.instagram_service import sync_instagram_subscriptions

router = APIRouter(prefix="/instagram", tags=["Instagram"])

@router.post(
    "/sync",
    response_model=InstagramDataRead,
    status_code=status.HTTP_200_OK,
    summary="Запустить синхронизацию подписок Instagram"
)
async def instagram_sync(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
      # Явно загружаем профиль из БД
    res = await db.execute(select(Profile).where(Profile.telegram_user_id == current_user.id))
    profile = res.scalar_one_or_none()

    if not profile or not profile.instagram_username:
        raise HTTPException(
            status_code=400,
            detail = "Сначала укажите instagram_username в своём профиле"
                                      )

    # Вызываем сервис
    instagram_data = await sync_instagram_subscriptions(
        telegram_user_id = current_user.telegram_user_id,
        instagram_username = profile.instagram_username,
        db = db
    )
    return instagram_data
