import uuid

import boto3
from botocore.exceptions import BotoCoreError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Any

from starlette.concurrency import run_in_threadpool

from core.database import get_db
from core.config import settings
from core.security import get_current_user
from models.profile import Profile
from models.user import User
from models.photo import Photo
from schemas.photo import PhotoRead
from utils.s3 import upload_file_to_s3, build_photo_urls

router = APIRouter(prefix="/photo", tags=["photo"])


@router.post(
    "/",
    response_model=PhotoRead,
    summary="Загрузить одно фото в профиль и вернуть его объект",
)
async def upload_photo(
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Any:
    # 1) Находим профиль текущего пользователя
    res = await db.execute(
        select(Profile.id).where(Profile.user_id == current_user.id)
    )
    profile_id = res.scalar_one_or_none()
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) Проверяем, чтобы не было более MAX_PHOTOS
    res2 = await db.execute(
        select(Photo.id).where(Photo.profile_id == profile_id)
    )
    if len(res2.scalars().all()) >= 6:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя иметь более {6} фото"
        )

    # 3) Загружаем файл в S3 (не блокируя loop)
    try:
        s3_key = await run_in_threadpool(
            upload_file_to_s3,
            photo.file,
            f"{current_user.id}_{uuid.uuid4().hex}",
            settings.AWS_S3_BUCKET_NAME
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload error: {e}")

    # 4) Сохраняем запись в БД
    new_photo = Photo(
        profile_id=profile_id,
        s3_key=s3_key,
        is_active=True
    )
    db.add(new_photo)
    await db.commit()
    await db.refresh(new_photo)

    # 5) Собираем URL
    base = settings.AWS_S3_ENDPOINT_URL.rstrip("/") + "/" + settings.AWS_S3_BUCKET_NAME
    url = f"{base}/{s3_key}"

    # 6) Возвращаем полный объект
    return PhotoRead(
        id=new_photo.id,
        profile_id=new_photo.profile_id,
        url=url,
        is_active=new_photo.is_active,
        created_at=new_photo.created_at,
    )


@router.get(
    "/",
    response_model=List[str],
    summary="Получить список всех фото профиля",
)
async def list_photos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    # 1) Находим профиль текущего пользователя
    res = await db.execute(
        select(Profile.id).where(Profile.user_id == current_user.id)
    )
    profile_id = res.scalar_one_or_none()
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) Строим и возвращаем список URL всех активных фото
    urls = await build_photo_urls(profile_id, db)
    # АБСОЛЮТНО ВАЖНО: вернуть список, даже если он пуст
    return urls


@router.delete(
    "/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить фото по ID и из S3",
)
async def delete_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) Проверяем, что такое фото у пользователя есть
    res = await db.execute(
        select(Photo).where(Photo.id == photo_id, Photo.profile_id == current_user.id)
    )
    photo = res.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # 2) Удаляем файл из S3 в отдельном потоке
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
    )
    try:
        await run_in_threadpool(
            s3_client.delete_object,
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=photo.s3_key,
        )
    except BotoCoreError as e:
        # Логируем ошибку, но продолжаем удаление из БД
        # можно подключить ваш логгер: logger.error(f"S3 delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3 delete error: {e}")

    # 3) Удаляем запись из БД
    await db.execute(delete(Photo).where(Photo.id == photo_id))
    await db.commit()

    return