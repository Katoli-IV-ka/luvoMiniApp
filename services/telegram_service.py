import asyncio
from typing import Optional

import requests

from core.config import settings

APP_URL = "https://vitalycatt-luvo-mini-app-c7dd.twc1.net/"


def _send_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть приложение",
                        "web_app": {"url": APP_URL},
                    }
                ]
            ]
        },
    }
    proxies: Optional[dict[str, str]] = None
    if settings.PROXY:
        proxies = {"http": settings.PROXY, "https": settings.PROXY}
    try:
        requests.post(url, json=payload, timeout=5, proxies=proxies)
    except requests.RequestException:
        pass


async def send_message(chat_id: int, text: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send_message, chat_id, text)


async def notify_like(chat_id: int) -> None:
    await send_message(chat_id, "Кому-то понравился твой профиль ❤️ Узнай, кто это")


async def notify_match(chat_id: int) -> None:
    await send_message(chat_id, "Совпадение! 🔥 У вас взаимный интерес — начни общение")
