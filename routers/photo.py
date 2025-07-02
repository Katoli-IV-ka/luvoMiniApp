import uuid

import boto3
from botocore.exceptions import BotoCoreError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import List, Any

from starlette.concurrency import run_in_threadpool

from core.database import get_db
from core.config import settings
from core.security import get_current_user
from models.profile import Profile
from models.user import User
from models.photo import Photo
from schemas.photo import PhotoRead
from utils.s3 import upload_file_to_s3, build_photo_urls, delete_file_from_s3

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
    except ValueError as ve:
        # неподдерживаемый формат / не изображение
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # сбой при работе с S3
        raise HTTPException(status_code=500, detail=str(e))

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
    response_model=List[PhotoRead],
    summary="Получить список всех активных фото профиля",
)
async def list_photos(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[PhotoRead]:
    # 1) Находим профиль
    res = await db.execute(
        select(Profile.id).where(Profile.user_id == current_user.id)
    )
    profile_id = res.scalar_one_or_none()
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) Достаём все активные Photo, отсортированные по created_at
    res2 = await db.execute(
        select(Photo)
        .where(Photo.profile_id == profile_id, Photo.is_active.is_(True))
        .order_by(Photo.created_at.asc())
    )
    photos = res2.scalars().all()

    # 3) Формируем базовый URL
    base = settings.AWS_S3_ENDPOINT_URL.rstrip("/") + "/" + settings.AWS_S3_BUCKET_NAME

    # 4) Собираем и возвращаем список PhotoRead
    result: List[PhotoRead] = []
    for p in photos:
        result.append(
            PhotoRead(
                id=p.id,
                profile_id=p.profile_id,
                url=f"{base}/{p.s3_key}",
                is_active=p.is_active,
                created_at=p.created_at,
            )
        )
    return result


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
    # 1) Проверяем, что у пользователя есть профиль
    res_profile = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    current_profile = res_profile.scalar_one_or_none()
    if not current_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) Проверяем, что фото принадлежит этому профилю
    res = await db.execute(
        select(Photo).where(
            Photo.id == photo_id,
            Photo.profile_id == current_profile.id,
        )
    )
    photo = res.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # 3) Нельзя удалять последнее фото
    total_photos = (
        await db.execute(
            select(func.count(Photo.id)).where(Photo.profile_id == current_profile.id)
        )
    ).scalar_one()
    if total_photos <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the last photo in profile"
        )

    # 4) Удаляем файл из S3 через нашу утилиту
    try:
        # запускаем синхронную функцию в пуле потоков
        await run_in_threadpool(
            delete_file_from_s3,
            photo.s3_key,
            settings.AWS_S3_BUCKET_NAME,
        )
    except Exception as e:
        # если S3 упало — возвращаем 500
        raise HTTPException(status_code=500, detail=str(e))

    # 5) Удаляем запись из базы
    await db.execute(delete(Photo).where(Photo.id == photo_id))
    await db.commit()

    # FastAPI автоматически вернёт 204 No Content
    return