# backend/routers/profile.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date
from typing import List, Optional

from core.database import get_db
from core.config import settings
from routers.auth import get_current_user             # Dependency из auth.py
from models.user import User
from models.profile import Profile
from models.photo import Photo
from schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from utils.s3 import upload_file_to_s3

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post(
    "/",
    response_model=ProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Onboarding: создать профиль и загрузить главное фото"
)
async def create_profile(
    first_name: str = Form(...),
    birthdate: date = Form(...),
    gender: str = Form(...),
    telegram_username: str = Form(...),
    instagram_username: Optional[str] = Form(None),
    about: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Проверяем, что профиль ещё не создан
    if current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )

    # 2. Создаем запись Profile
    profile = Profile(
        user_id=current_user.id,
        first_name=first_name,
        birthdate=birthdate,
        gender=gender,
        telegram_username=telegram_username,
        instagram_username=instagram_username,
        about=about,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # 3. Загружаем главное фото в S3
    try:
        s3_key = upload_file_to_s3(file.file, file.filename, settings.AWS_S3_BUCKET_NAME)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photo: {e}"
        )
    photo = Photo(profile_id=profile.id, s3_key=s3_key, is_active=True)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    # 4. Собираем публичные URL всех активных фото
    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    photo_urls = [
        f"{base_url}/{bucket}/{p.s3_key}"
        for p in profile.photos if p.is_active
    ]

    # 5. Формируем и возвращаем ProfileRead
    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        birthdate=profile.birthdate,
        gender=profile.gender,
        about=profile.about,
        telegram_username=profile.telegram_username,
        instagram_username=profile.instagram_username,
        photos=photo_urls,
        created_at=profile.created_at,
    )


@router.get(
    "/me",
    response_model=ProfileRead,
    summary="Получить собственный профиль"
)
async def read_my_profile(
    current_user: User = Depends(get_current_user),
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    photo_urls = [
        f"{base_url}/{bucket}/{p.s3_key}"
        for p in profile.photos if p.is_active
    ]

    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        birthdate=profile.birthdate,
        gender=profile.gender,
        about=profile.about,
        telegram_username=profile.telegram_username,
        instagram_username=profile.instagram_username,
        photos=photo_urls,
        created_at=profile.created_at,
    )


@router.patch(
    "/",
    response_model=ProfileRead,
    summary="Редактировать данные профиля"
)
async def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    for field, value in profile_in.dict(exclude_unset=True).items():
        setattr(profile, field, value)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    photo_urls = [
        f"{base_url}/{bucket}/{p.s3_key}"
        for p in profile.photos if p.is_active
    ]

    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        birthdate=profile.birthdate,
        gender=profile.gender,
        about=profile.about,
        telegram_username=profile.telegram_username,
        instagram_username=profile.instagram_username,
        photos=photo_urls,
        created_at=profile.created_at,
    )


@router.post(
    "/photos",
    response_model=List[str],
    summary="Загрузить дополнительное фото (максимум 6 штук)"
)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    active_photos = [p for p in profile.photos if p.is_active]
    if len(active_photos) >= 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max 6 photos allowed")

    try:
        s3_key = upload_file_to_s3(file.file, file.filename, settings.AWS_S3_BUCKET_NAME)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    photo = Photo(profile_id=profile.id, s3_key=s3_key, is_active=True)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    return [
        f"{base_url}/{bucket}/{p.s3_key}"
        for p in profile.photos if p.is_active
    ]


@router.delete(
    "/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить фото профиля"
)
async def delete_photo(
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    stmt = select(Photo).where(Photo.id == photo_id, Photo.profile_id == profile.id)
    result = await db.execute(stmt)
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    photo.is_active = False
    db.add(photo)
    await db.commit()
    # 204 No Content → тело не возвращаем
