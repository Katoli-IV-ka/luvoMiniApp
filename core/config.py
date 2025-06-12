from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_S3_ENDPOINT_URL: str
    AWS_S3_REGION: str
    SECRET_KEY: str



    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаём глобальный объект, который будем импортировать везде
settings = Settings()
