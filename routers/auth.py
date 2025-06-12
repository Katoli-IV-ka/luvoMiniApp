# backend/routers/auth.py
import json

from fastapi import APIRouter

from schemas.auth import TokenResponse, InitDataSchema
from schemas.user import UserRead, UserCreate
from models.profile import Profile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.security import verify_init_data
from core.config import settings
from core.database import get_db
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

# OAuth2 схема, будет читать Bearer-токен из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login",response_model=TokenResponse,summary="Login через Telegram WebApp initData → выдаёт JWT")
async def login(
    init_data: InitDataSchema,
    db: AsyncSession = Depends(get_db),
):
    # 1) валидируем подпись и парсим init_data
    data = verify_init_data(init_data.init_data)
    user_obj = data.get("user")
    if not user_obj:
        raise HTTPException(status_code=400, detail="Missing 'user' in init_data")
    user_data = json.loads(user_obj)
    tg_id = user_data.get("id")
    if not tg_id:
        raise HTTPException(status_code=400, detail="Invalid 'user' data in init_data")

    # 2) ищем или создаём User
    stmt = select(User).where(User.telegram_user_id == tg_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_user_id=tg_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 3) генерируем JWT
    token_payload = {"user_id": user.id}
    access_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

    # 4) проверяем, есть ли профиль
    stmt_profile = select(Profile.id).where(Profile.user_id == user.id).limit(1)
    result_profile = await db.execute(stmt_profile)
    has_profile = result_profile.scalar_one_or_none() is not None

    # 5) возвращаем токен и флаг наличия профиля
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        has_profile=has_profile,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get(
    "/me",
    response_model=TokenResponse,
    summary="Проверить JWT и узнать, существует ли профиль"
)
async def whoami(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Явная проверка наличия профиля через отдельный запрос
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    result = await db.execute(stmt)
    has_profile = result.scalar_one_or_none() is not None

    return TokenResponse(
        access_token="",           # или можно не возвращать access_token здесь вовсе
        token_type="bearer",
        has_profile=has_profile,
    )


@router.post("/register", response_model=UserRead)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # 1) Проверяем, существует ли уже пользователь с таким telegram_user_id
    stmt = select(User).where(User.telegram_user_id == user_in.telegram_user_id)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered")

    # 2) Создаём пользователя
    new_user = User(
        telegram_user_id=user_in.telegram_user_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user