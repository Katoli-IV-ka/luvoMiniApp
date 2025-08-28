import asyncio
import threading
import time
from typing import Optional

import requests

from core.config import settings

APP_URL = "https://vitalycatt-luvo-mini-app-c7dd.twc1.net/"
START_TEXT = (
    "Привет! 👋 Добро пожаловать в приложение для знакомств Luvo ✨ "
    "Мы помогаем найти новые знакомства на основе ваших подписок в Instagram. "
    "Чтобы начать знакомиться, запусти приложение 🚀"
)

_stop_event = threading.Event()
_bot_thread: Optional[threading.Thread] = None


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

def _poll_updates() -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    offset: Optional[int] = None
    proxies: Optional[dict[str, str]] = None
    if settings.PROXY:
        proxies = {"http": settings.PROXY, "https": settings.PROXY}
    while not _stop_event.is_set():
        params: dict[str, int] = {"timeout": 10}
        if offset is not None:
            params["offset"] = offset + 1
        try:
            resp = requests.get(url, params=params, timeout=30, proxies=proxies)
            data = resp.json()
            for update in data.get("result", []):
                offset = update.get("update_id", offset)
                message = update.get("message") or {}
                text = message.get("text")
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                if text == "/start" and chat_id is not None:
                    _send_message(chat_id, START_TEXT)
        except requests.RequestException:
            time.sleep(1)


def start_bot() -> None:
    global _bot_thread
    _stop_event.clear()
    _bot_thread = threading.Thread(target=_poll_updates, daemon=True)
    _bot_thread.start()


def stop_bot() -> None:
    _stop_event.set()
    if _bot_thread and _bot_thread.is_alive():
        _bot_thread.join(timeout=1)
