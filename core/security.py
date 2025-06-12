# core/security.py
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import parse_qsl
from fastapi import HTTPException, status

from core.config import settings

def verify_init_data(init_data: str, max_age_seconds: int = 86_400) -> dict:
    """
    Проверяет подпись Telegram.WebApp.initData и возвращает словарь всех параметров,
    кроме hash. Бросает HTTPException(403), если подпись не совпадает,
    или (400), если формат данных неверен.

    Алгоритм в соответствии с рекомендациями Telegram:
    1. parse_qsl → dict (авто-decode percent-encoding)
    2. извлечь hash и убрать из dict
    3. собрать data_check_string: отсортированные пары "key=value" через "\n"
    4. secret_key = HMAC-SHA256(key=b"WebAppData", msg=BOT_TOKEN)
    5. calculated_hash = HMAC-SHA256(key=secret_key, msg=data_check_string).hexdigest()
    6. сравнить calculated_hash и hash_received
    7. проверить, что auth_date не старее max_age_seconds (по желанию)
    """
    # 1. Парсим query string
    data_list = parse_qsl(init_data, keep_blank_values=True)
    data = dict(data_list)

    # 2. Достаём переданный hash
    hash_received = data.pop("hash", None)
    if not hash_received:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'hash' in init_data"
        )

    # 3. Собираем data_check_string
    data_check_arr = [f"{key}={data[key]}" for key in sorted(data.keys())]
    data_check_string = "\n".join(data_check_arr)

    # 4. Формируем ключ HMAC из BOT_TOKEN
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    # 5. Вычисляем итоговую подпись
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    # 6. Constant-time сравнение
    if not hmac.compare_digest(computed_hash, hash_received):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid init_data signature"
        )

    # 7. Опционально: проверка актуальности auth_date
    auth_date = data.get("auth_date")
    if auth_date and auth_date.isdigit():
        ts = int(auth_date)
        dt = datetime.utcfromtimestamp(ts)
        if datetime.utcnow() - dt > timedelta(seconds=max_age_seconds):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="init_data is too old"
            )

    # Возвращаем все валидные поля (user, query_id, auth_date и т.д.)
    return data
