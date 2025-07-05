import requests
from typing import Optional, List
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.user import User
from models.instagram_data import InstagramData
from models.instagram_connection import InstagramConnection

# Настройки прокси и RapidAPI
PROXIES = {
    "http":  settings.PROXY,
    "https": settings.PROXY,
}
API_HEADERS = {
    "x-rapidapi-key": settings.RAPIDAPI_KEY,
    "x-rapidapi-host": "instagram-scrapper-posts-reels-stories-downloader.p.rapidapi.com"
}


def get_user_id_by_username(username: str) -> Optional[int]:
    url = "https://instagram-scrapper-posts-reels-stories-downloader.p.rapidapi.com/user_id_by_username"
    params = {"username": username}
    try:
        resp = requests.get(
            url,
            headers=API_HEADERS,
            params=params,
            proxies=PROXIES,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("UserID")
    except requests.RequestException as e:
        print("Ошибка при get_user_id:", e)
        return None


def get_following_by_user_id(user_id: int) -> List[str]:
    url = "https://instagram-scrapper-posts-reels-stories-downloader.p.rapidapi.com/followings_by_user_id"
    params = {"user_id": user_id}
    try:
        resp = requests.get(
            url,
            headers=API_HEADERS,
            params=params,
            proxies=PROXIES,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        # возвращаем список username из поля 'users'
        return [u["username"] for u in data.get("users", [])]
    except requests.RequestException as e:
        print("Ошибка при get_following:", e)
        return []


async def sync_instagram_subscriptions(
    telegram_user_id: int,
    instagram_username: str,
    db: AsyncSession
) -> InstagramData:
    """
    1) Получаем наших пользователя и профиль по telegram_user_id.
    2) Синхронно (в пуле) запрашиваем UserID Instagram и список подписок.
    3) Обновляем таблицу instagram_data.
    4) Пересоздаём связи в instagram_connections для всех совпадающих Luvo-пользователей.
    """
    # Шаг 1: находим User
    result = await db.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Telegram user not found")

    # Шаг 2a: заходим в Instagram, получаем numeric ID
    ig_user_id = await run_in_threadpool(get_user_id_by_username, instagram_username)
    if not ig_user_id:
        raise HTTPException(status_code=400, detail="Не удалось получить Instagram UserID")

    # Шаг 2b: получаем список username, на которых он подписан
    following_usernames = await run_in_threadpool(get_following_by_user_id, ig_user_id)

    # Шаг 3: обновляем/создаём InstagramData
    result = await db.execute(
        select(InstagramData).where(InstagramData.user_id == user.id)
    )
    ig_data = result.scalar_one_or_none()
    if ig_data:
        ig_data.ig_username = instagram_username
        ig_data.subscriptions = following_usernames
        ig_data.last_sync = func.now()
    else:
        ig_data = InstagramData(
            user_id=user.id,
            ig_username=instagram_username,
            subscriptions=following_usernames
        )
        db.add(ig_data)

    # Шаг 4a: находим в Luvo-профилях совпадения по instagram_username
    result = await db.execute(
        select(User.user_id)
        .where(User.instagram_username.in_(following_usernames))
    )
    matching_ids = [r[0] for r in result.all()]

    # Шаг 4b: удаляем старые связи для текущего пользователя
    await db.execute(
        delete(InstagramConnection)
        .where(InstagramConnection.user_id == user.id)
    )

    # Шаг 4c: вставляем новые связи subscription/follower
    for other_id in matching_ids:
        # я подписан на них
        db.add(InstagramConnection(
            user_id=user.id,
            connected_id=other_id,
            type="subscription"
        ))
        # и они подписаны на меня (обратная связь)
        db.add(InstagramConnection(
            user_id=other_id,
            connected_id=user.id,
            type="follower"
        ))

    await db.commit()
    await db.refresh(ig_data)
    return ig_data
