# services/telegram_service.py

import requests
from fastapi.concurrency import run_in_threadpool

from core.config import settings


WEB_APP_URL = "https://vitalycatt-luvo-mini-app-c7dd.twc1.net/"
API_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"


async def _send_message(chat_id: int, text: str) -> None:
    """Отправка сообщения в Telegram с кнопкой открытия приложения."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть приложение",
                        "web_app": {"url": WEB_APP_URL},
                    }
                ]
            ]
        },
    }
    try:
        await run_in_threadpool(
            requests.post,
            API_URL,
            json=payload,
            timeout=10,
        )
    except requests.RequestException as exc:
        print("Ошибка отправки сообщения Telegram:", exc)


async def send_like_notification(chat_id: int) -> None:
    """Уведомление о входящем лайке."""
    await _send_message(
        chat_id,
        "Кому-то понравился твой профиль ❤️ Узнай, кто это",
    )


async def send_match_notification(chat_id: int) -> None:
    """Уведомление о новом мэтче."""
    await _send_message(
        chat_id,
        "Совпадение! 🔥 У вас взаимный интерес — начни общение",
    )

