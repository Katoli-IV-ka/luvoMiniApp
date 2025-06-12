# backend/routers/profile.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date
from typing import List, Optional

from core.database import get_db
from core.config import settings
from routers.auth import get_current_user
from models.user import User
from models.profile import Profile
from models.photo import Photo
from schemas.profile import ProfileRead, ProfileCreate, ProfileUpdate
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
    # Явно проверяем, есть ли профиль в БД
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists")

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

    # Загружаем главное фото
    try:
        s3_key = upload_file_to_s3(file.file, file.filename, settings.AWS_S3_BUCKET_NAME)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    photo = Photo(profile_id=profile.id, s3_key=s3_key, is_active=True)
    db.add(photo)
    await db.commit()

    # Составляем список URL фотографий
    base = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    stmt_photos = select(Photo).where(Photo.profile_id == profile.id, Photo.is_active == True)
    res_ph = await db.execute(stmt_photos)
    photos = res_ph.scalars().all()
    photo_urls = [f"{base}/{bucket}/{ph.s3_key}" for ph in photos]

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
    summary="Получить свой профиль"
)
async def read_my_profile(
    current_user: User = Depends(get_current_user),
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    photo_urls = [f"{base_url}/{bucket}/{p.s3_key}" for p in profile.photos if p.is_active]

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
    summary="Получить свой профиль"
)
async def read_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) вытягиваем Profile + все его photos в одном await
    stmt = (
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 2) формируем URL только для активных фото
    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket   = settings.AWS_S3_BUCKET_NAME
    photo_urls = [
        f"{base_url}/{bucket}/{photo.s3_key}"
        for photo in profile.photos
        if photo.is_active
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
    summary="Загрузить доп. фото (до 6 штук)"
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload photo: {e}")

    photo = Photo(profile_id=profile.id, s3_key=s3_key, is_active=True)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    base_url = settings.AWS_S3_ENDPOINT_URL.rstrip("/")
    bucket = settings.AWS_S3_BUCKET_NAME
    return [f"{base_url}/{bucket}/{p.s3_key}" for p in profile.photos if p.is_active]


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
    result = await db.execute(
        select(Photo).where(Photo.id == photo_id, Photo.profile_id == current_user.profile.id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    photo.is_active = False
    db.add(photo)
    await db.commit()
