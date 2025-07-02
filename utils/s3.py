import uuid
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.photo import Photo
from utils.image_tools import compress_image_bytes

# ==== Настройка клиента MinIO ====
_endpoint = settings.AWS_S3_ENDPOINT_URL.replace("https://", "").replace("http://", "")
_s3 = Minio(
    _endpoint,
    access_key=settings.AWS_ACCESS_KEY_ID,
    secret_key=settings.AWS_SECRET_ACCESS_KEY,
    region=settings.AWS_S3_REGION,
    secure=False  # по договорённости без TLS
)


def upload_file_to_s3(
    file_like,
    file_name: str,
    bucket_name: str
) -> str:
    """
    Сжимает изображение через compress_image_bytes и кладёт в S3.
    Бросает ValueError, если файл не изображение.
    Бросает Exception, если проблемы с S3.
    """
    # 1) читаем весь файл в байты
    data = file_like.read()

    # 2) сжимаем и получаем расширение
    compressed_data, ext = compress_image_bytes(data, quality=90)

    # 3) генерируем ключ с правильным расширением
    s3_key = f"profiles/{file_name}_{uuid.uuid4().hex}.{ext}"

    # 4) заливаем в S3/MinIO
    try:
        _s3.put_object(
            bucket_name,
            s3_key,
            BytesIO(compressed_data),
            length=len(compressed_data),
            content_type=f"image/{ext}"
        )
    except S3Error as e:
        raise Exception(f"Ошибка при загрузке в S3: {e}")

    return s3_key


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
