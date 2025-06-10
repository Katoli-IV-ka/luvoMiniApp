# backend/routers/profile.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.database import get_db
from models.photo import Photo
from models.profile import Profile
from models.user import User
from schemas.profile import ProfileRead, ProfileCreate, ProfileUpdate

from utils.s3 import upload_file_to_s3

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/photo", response_model=ProfileRead)
async def upload_profile_photo(
    telegram_user_id: int,  # получаем user_id из токена
    file: UploadFile = File(...),  # загружаем файл
    db: AsyncSession = Depends(get_db),
):
    # Найдём пользователя
    stmt_user = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt_user)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получим профиль пользователя
    stmt_profile = select(Profile).where(Profile.user_id == user.id)
    profile = (await db.execute(stmt_profile)).scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Загружаем фото в S3
    file_name = file.filename
    s3_key = upload_file_to_s3(file.file, file_name, settings.AWS_S3_BUCKET_NAME)

    # Добавляем фото в профиль
    new_photo = Photo(profile_id=profile.id, s3_key=s3_key)
    db.add(new_photo)
    await db.commit()
    await db.refresh(new_photo)

    # Обновляем ответ с фотографией
    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        birthdate=profile.birthdate,
        gender=profile.gender,
        about=profile.about,
        latitude=profile.latitude,
        longitude=profile.longitude,
        created_at=profile.created_at,
        photos=[new_photo.s3_key]
    )

@router.post("/", response_model=ProfileRead)
async def create_profile(
    profile_in: ProfileCreate,
    telegram_user_id: int,  # в реальности передаётся через токен/Depends
    db: AsyncSession = Depends(get_db),
):
    """
    Создать профиль для пользователя.
    Предполагается, что таблица User уже содержит запись с данным telegram_user_id.
    """
    # 1) Найдём User → ему поставим связь в Profile
    from models.user import User  # локальный импорт, чтобы избежать круговых
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 2) Проверим, нет ли у пользователя уже профиля
    stmt2 = select(Profile).where(Profile.user_id == user.id)
    existing = (await db.execute(stmt2)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists")

    # 3) Создаём профиль
    new_profile = Profile(
        user_id=user.id,
        first_name=profile_in.first_name,
        birthdate=profile_in.birthdate,
        gender=profile_in.gender,
        about=profile_in.about,
        latitude=profile_in.latitude,
        longitude=profile_in.longitude,
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    return new_profile


@router.get("/me", response_model=ProfileRead)
async def get_my_profile(
    telegram_user_id: int,  # в реальности — из токена
    db: AsyncSession = Depends(get_db),
):
    from models.user import User
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt2 = select(Profile).where(Profile.user_id == user.id)
    profile = (await db.execute(stmt2)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return profile

"""
@router.put("/", response_model=ProfileRead)
async def update_my_profile(
    profile_in: ProfileUpdate,
    telegram_user_id: int,  # в реальности — из токена
    db: AsyncSession = Depends(get_db),
):
    from models.user import User
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt2 = select(Profile).where(Profile.user_id == user.id)
    profile = (await db.execute(stmt2)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # Обновляем поля, которые пришли в profile_in
    for field, value in profile_in.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
"""