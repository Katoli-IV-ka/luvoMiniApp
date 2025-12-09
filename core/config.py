from typing import Optional

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_S3_ENDPOINT_URL: str
    AWS_S3_REGION: str
    PROXY: str
    RAPIDAPI_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    IMPORT_FROM_S3_PASSWORD: Optional[str] = None
    DEBUG: bool

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаём глобальный объект, который будем импортировать везде
settings = Settings()
