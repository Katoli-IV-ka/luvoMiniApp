from typing import Dict, List, Optional

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str
    ADMIN_REVIEW_CHAT_ID: int
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_S3_ENDPOINT_URL: str
    AWS_S3_REGION: str
    PROXY: Optional[str] = None
    RAPIDAPI_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    PLACEHOLDER_PHOTO_S3_KEY: str
    PLACEHOLDER_NAME: str
    PLACEHOLDER_BIO: str

    SEED_DB: bool
    RESET_DB_ON_STARTUP: bool
    DEBUG: bool
    DEBUG_TELEGRAM_BOT_TOKENS: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def proxies(self) -> Optional[Dict[str, str]]:
        if not self.PROXY:
            return None
        return {"http": self.PROXY, "https": self.PROXY}

    @property
    def s3_base_url(self) -> str:
        endpoint = self.AWS_S3_ENDPOINT_URL.rstrip("/")
        return f"{endpoint}/{self.AWS_S3_BUCKET_NAME}"

    @property
    def s3_endpoint_host(self) -> str:
        return self.AWS_S3_ENDPOINT_URL.replace("https://", "").replace("http://", "")

    def get_debug_telegram_bot_tokens(self) -> List[str]:
        """Return sanitized debug tokens specified via CSV."""
        if not self.DEBUG_TELEGRAM_BOT_TOKENS:
            return []
        tokens = [token.strip() for token in self.DEBUG_TELEGRAM_BOT_TOKENS.split(",")]
        return [token for token in tokens if token]


# Создаём глобальный объект, который будем импортировать везде
settings = Settings()
