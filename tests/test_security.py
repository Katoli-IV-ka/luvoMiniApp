import hmac
from datetime import datetime
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

from core.config import settings
from core.security import verify_init_data


def _build_init_data(token: str, payload: dict) -> str:
    data_check_arr = [f"{key}={payload[key]}" for key in sorted(payload.keys())]
    data_check_string = "\n".join(data_check_arr)
    secret_key = hmac.new(key=b"WebAppData", msg=token.encode("utf-8"), digestmod="sha256").digest()
    hash_value = hmac.new(key=secret_key, msg=data_check_string.encode("utf-8"), digestmod="sha256").hexdigest()
    full_payload = {**payload, "hash": hash_value}
    return urlencode(full_payload)


@pytest.fixture(autouse=True)
def reset_settings():
    original = {
        "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
        "DEBUG": settings.DEBUG,
        "DEBUG_TELEGRAM_BOT_TOKENS": settings.DEBUG_TELEGRAM_BOT_TOKENS,
    }
    try:
        yield
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


def test_verify_init_data_accepts_debug_tokens_when_enabled():
    base_data = {
        "auth_date": str(int(datetime.utcnow().timestamp())),
        "query_id": "q1",
        "user": "{\"id\":1}",
    }

    settings.DEBUG = True
    settings.TELEGRAM_BOT_TOKEN = "primary-token"
    settings.DEBUG_TELEGRAM_BOT_TOKENS = "extra-one, fallback-token"

    init_data = _build_init_data("fallback-token", base_data)
    assert verify_init_data(init_data) == base_data


def test_verify_init_data_rejects_debug_tokens_when_disabled():
    base_data = {
        "auth_date": str(int(datetime.utcnow().timestamp())),
        "query_id": "q2",
    }

    settings.DEBUG = False
    settings.TELEGRAM_BOT_TOKEN = "primary-token"
    settings.DEBUG_TELEGRAM_BOT_TOKENS = "fallback-token"

    init_data = _build_init_data("fallback-token", base_data)

    with pytest.raises(HTTPException) as exc:
        verify_init_data(init_data)

    assert exc.value.status_code == 403
