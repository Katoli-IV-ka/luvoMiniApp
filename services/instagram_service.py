# services/instagram_service.py

import os
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from instagrapi import Client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from models.user import User
from models.profile import Profile
from models.instagram_data import InstagramData
from core.config import settings  # чтобы брать IG_SERVICE_USERNAME/PASSWORD

SESSION_DIR = os.path.join(os.getcwd(), "instagram_session")
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_FILE = os.path.join(SESSION_DIR, "service_account.json")


async def get_instagram_client() -> Client:
    """
    Возвращает авторизованный instagrapi.Client,
    загружая сохранённые куки или логинясь в первый раз.
    """
    client = Client()
    # Попробуем загрузить прошлую сессию
    try:
        client.load_settings(SESSION_FILE)
    except Exception:
        pass

    # Если не залогинены — логинимся
    if not client.user_id:
        username = settings.IG_SERVICE_USERNAME
        password = settings.IG_SERVICE_PASSWORD
        if not username or not password:
            raise HTTPException(
                status_code=500,
                detail="Не заданы IG_SERVICE_USERNAME/IG_SERVICE_PASSWORD в .env"
            )
        try:
            # синхронная авторизация в потоке
            await run_in_threadpool(client.login, username, password)
            # сохраняем куки
            client.dump_settings(SESSION_FILE)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Не удалось залогиниться в Instagram: {e}")
    return client


async def sync_instagram_subscriptions(
    telegram_user_id: int,
    instagram_username: str,
    db: AsyncSession
) -> InstagramData:
    # 1) Находим пользователя
    result = await db.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Telegram-пользователь не найден")

    # 2) Запускаем авторизованный клиент
    client = await get_instagram_client()

    # 3) Получаем ig_user_id и список подписок
    try:
        ig_user = await run_in_threadpool(client.user_info_by_username, instagram_username)
        following_dict = await run_in_threadpool(client.user_following, ig_user.pk)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка Instagram API: {e}")

    following_usernames = [u.username for u in following_dict.values()]

    # 4) Ищем совпадения в наших профилях
    result = await db.execute(
        select(Profile.telegram_user_id)
        .where(Profile.instagram_username.in_(following_usernames))
    )
    matching_ids = [r[0] for r in result.all()]

    # 5) Сохраняем данные в instagram_data
    stmt = select(InstagramData).where(InstagramData.user_id == user.id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.ig_username = instagram_username
        existing.subscriptions = following_usernames
        existing.last_sync = func.now()
        instagram_data = existing
    else:
        instagram_data = InstagramData(
            user_id=user.id,
            ig_username=instagram_username,
            subscriptions=following_usernames,
        )
        db.add(instagram_data)

    await db.commit()
    await db.refresh(instagram_data)
    return instagram_data
