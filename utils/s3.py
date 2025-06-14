# backend/utils/s3.py
import boto3
import uuid

from botocore.exceptions import NoCredentialsError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.photo import Photo


# Настройки для подключения к S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    region_name=settings.AWS_S3_REGION,
)

def upload_file_to_s3(file, file_name: str, bucket_name: str):
    """
    Загружает файл в указанный бакет S3.
    """
    try:
        # Генерируем уникальный ключ для файла
        s3_key = f"profiles/{file_name}_{uuid.uuid4().hex}.jpg"
        s3.upload_fileobj(file, bucket_name, s3_key)
        return s3_key
    except NoCredentialsError:
        raise Exception("Credentials not available")


async def build_photo_urls(profile_id: int, db: AsyncSession) -> list[str]:

    # достаём только ключи из таблицы photos
    result = await db.execute(
        select(Photo.s3_key)
        .where(Photo.profile_id == profile_id, Photo.is_active == True)
        .order_by(Photo.created_at.asc())
    )
    keys = [row[0] for row in result.all()]

    base = settings.AWS_S3_ENDPOINT_URL.rstrip("/") + "/" + settings.AWS_S3_BUCKET_NAME
    return [f"{base}/{key}" for key in keys]