# core/security.py
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import parse_qsl
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from core.config import settings
from core.database import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if settings.DEBUG:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No users in database to impersonate in DEBUG mode"
            )
        return user

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.TELEGRAM_BOT_TOKEN, algorithms=["HS256"])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


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
    data_list = parse_qsl(init_data, keep_blank_values=True)
    data = dict(data_list)

    hash_received = data.pop("hash", None)
    if not hash_received:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'hash' in init_data"
        )

    data_check_arr = [f"{key}={data[key]}" for key in sorted(data.keys())]
    data_check_string = "\n".join(data_check_arr)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, hash_received):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid init_data signature"
        )

    auth_date = data.get("auth_date")
    if auth_date and auth_date.isdigit():
        ts = int(auth_date)
        dt = datetime.utcfromtimestamp(ts)
        if datetime.utcnow() - dt > timedelta(seconds=max_age_seconds):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="init_data is too old"
            )

    return data