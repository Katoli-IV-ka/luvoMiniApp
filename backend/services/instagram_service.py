# backend/services/instagram_service.py
from instagrapi import Client
from core.config import settings
from models.instagram_data import InstagramData
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.user import User
from typing import List


async def sync_instagram_subscriptions(telegram_user_id: int, instagram_username: str, db: AsyncSession):
    """
    Синхронизация подписок с Instagram для пользователя, используя только Instagram username.
    """
    # 1. Получаем пользователя по telegram_user_id
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        return None  # Если пользователя нет в базе

    # 2. Подключаемся к Instagram с помощью instagrapi через публичный API
    cl = Client()
    try:
        # Авторизация с использованием только username
        cl.login_by_username(instagram_username)
    except Exception as e:
        raise Exception(f"Ошибка при подключении к Instagram: {str(e)}")

    # Получаем список подписок
    user_id = cl.user_id_from_username(instagram_username)
    subscriptions = cl.user_following(user_id)

    # Получаем список всех зарегистрированных пользователей в Luvo
    registered_users_stmt = select(User).where(User.instagram_username.isnot(None))
    registered_users = (await db.execute(registered_users_stmt)).scalars().all()

    # Получаем список подписок, которые зарегистрированы в нашей базе
    matching_users = [
        user for user in registered_users if user.instagram_username in [sub.username for sub in subscriptions]
    ]

    # Сохраняем найденные совпадения
    instagram_data = InstagramData(
        user_id=user.id,
        ig_username=instagram_username,
        subscriptions=",".join([sub.username for sub in subscriptions]),
        matched_users=[user.id for user in matching_users]
    )

    db.add(instagram_data)
    await db.commit()

    return instagram_data
