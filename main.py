from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine
from models.base import Base
from utils.drop_db import async_drop_database

from routers.auth import router as auth_router
from routers.profile import router as profile_router
from routers.feed import router as feed_router
from routers.like import router as like_router
from routers.match import router as match_router
from routers.photo import router as photo_router

from utils.seed_db import seed


app = FastAPI(
    title="Luvo MiniApp Backend",
    version="0.1.0",
    description="Backend для Telegram Mini-App «Luvo»"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(feed_router)
app.include_router(like_router)
app.include_router(match_router)
app.include_router(photo_router)


@app.on_event("startup")
async def on_startup():
    if settings.RESET_DB_ON_STARTUP == "true":
        await async_drop_database()

    if settings.SEED_DB == "true":
        await seed()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "Luvo MiniApp Backend"}