# backend/utils/s3.py
import boto3
from botocore.exceptions import NoCredentialsError
from core.config import settings
import uuid

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
