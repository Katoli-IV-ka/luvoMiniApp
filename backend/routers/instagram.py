# backend/routers/instagram.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.instagram_service import sync_instagram_subscriptions
from models.instagram_data import InstagramData
from models.user import User
from schemas.instagram import InstagramDataRead, InstagramDataCreate


router = APIRouter(prefix="/instagram", tags=["instagram"])

@router.post("/sync", response_model=InstagramDataRead)
async def sync_instagram(
    telegram_user_id: int,  # в реальности будет передаваться через токен
    db: AsyncSession = Depends(get_db),
):
    # Синхронизируем подписки Instagram
    instagram_data = await sync_instagram_subscriptions(telegram_user_id, db)

    if not instagram_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found or not connected.")

    return InstagramDataRead(
        user_id=instagram_data.user_id,
        ig_username=instagram_data.ig_username,
        subscriptions=instagram_data.subscriptions,
    )

@router.put("/update", response_model=InstagramDataCreate)
async def update_instagram_data(
    instagram_data_in: InstagramDataCreate,
    telegram_user_id: int,  # получаем user_id из токена
    db: AsyncSession = Depends(get_db),
):
    # 1) Находим пользователя по telegram_user_id
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2) Если Instagram Data уже существует, обновляем
    stmt_instagram = select(InstagramData).where(InstagramData.user_id == user.id)
    instagram_data = (await db.execute(stmt_instagram)).scalar_one_or_none()

    if instagram_data:
        instagram_data.ig_username = instagram_data_in.ig_username
        instagram_data.subscriptions = ",".join(instagram_data_in.subscriptions)  # Обновляем подписки
    else:
        # Если данных Instagram нет — создаём новые
        instagram_data = InstagramData(
            user_id=user.id,
            ig_username=instagram_data_in.ig_username,
            subscriptions=",".join(instagram_data_in.subscriptions)
        )
        db.add(instagram_data)

    await db.commit()
    await db.refresh(instagram_data)

    return InstagramDataCreate(
        ig_username=instagram_data.ig_username,
        subscriptions=instagram_data.subscriptions.split(",")  # Конвертируем обратно в список
    )