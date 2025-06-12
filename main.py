# backend/main.py
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine
from models.base import Base

# Импортируем все модели, чтобы SQLAlchemy знала обо всех таблицах
from models.user import User
from models.profile import Profile
from models.photo import Photo
from models.like import Like
from models.match import Match
from models.feed_view import FeedView
from models.instagram_data import InstagramData

from routers.auth import router as auth_router
from routers.profile import router as profile_router
from routers.feed import router as feed_router
from utils.reset_db import async_reset_database

app = FastAPI(
    title="Luvo MiniApp Backend",
    version="0.1.0",
    description="Backend для Telegram Mini-App «Luvo»"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Или список ваших фронтенд-адресов
    allow_credentials=True,     # Если используете куки или авторизацию
    allow_methods=["*"],        # GET, POST, PATCH и т.д.
    allow_headers=["*"],        # Content-Type, Authorization и др.
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(feed_router)

@app.on_event("startup")
async def on_startup():
    """
    При старте приложения создаём все таблицы (если их нет) на основе Base.metadata.
    """
    if os.getenv("RESET_DB_ON_STARTUP", "").lower() == "true":
        # Асинхронный вызов
        await async_reset_database()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "Luvo MiniApp Backend запущен. Версия 0.1.0"}

@app.get("/ping")
async def ping():
    return {"pong": True}