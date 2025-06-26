import uuid
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.photo import Photo

# ==== Настройка клиента MinIO ====
_endpoint = settings.AWS_S3_ENDPOINT_URL.replace("https://", "").replace("http://", "")
_s3 = Minio(
    _endpoint,
    access_key=settings.AWS_ACCESS_KEY_ID,
    secret_key=settings.AWS_SECRET_ACCESS_KEY,
    region=settings.AWS_S3_REGION,
    secure=False  # по договорённости без TLS
)


def upload_file_to_s3(file, file_name: str, bucket_name: str) -> str:
    """
    Загружает file-like объект (UploadFile.file) в указанный бакет MinIO/S3.
    Возвращает сгенерированный ключ (s3_key).
    Сигнатура совпадает с прежней: upload_file_to_s3(file, file_name, bucket_name)
    """
    try:
        # Генерируем уникальный ключ для файла
        s3_key = f"profiles/{file_name}_{uuid.uuid4().hex}.jpg"

        # Читаем всё содержимое и оборачиваем в поток
        data = file.read()
        stream = BytesIO(data)

        # Загружаем в MinIO
        _s3.put_object(
            bucket_name,
            s3_key,
            stream,
            length=len(data),
            content_type="application/octet-stream"
        )

        return s3_key

    except S3Error as e:
        raise Exception(f"Ошибка при загрузке в S3: {e}")


def delete_file_from_s3(s3_key: str, bucket_name: str) -> None:
    """
    Удаляет объект из MinIO/S3.
    """
    try:
        _s3.remove_object(bucket_name, s3_key)
    except S3Error as e:
        raise Exception(f"Ошибка при удалении из S3: {e}")


async def build_photo_urls(profile_id: int, db: AsyncSession) -> list[str]:
    """
    Собирает публичные URL всех фото профиля.
    Сигнатура и поведение совпадают с прежней функцией.
    """
    result = await db.execute(
        select(Photo.s3_key)
        .where(Photo.profile_id == profile_id)
        .order_by(Photo.created_at.asc())
    )
    keys = [row[0] for row in result.all()]

    base = settings.AWS_S3_ENDPOINT_URL.rstrip("/") + "/" + settings.AWS_S3_BUCKET_NAME
    return [f"{base}/{key}" for key in keys]
