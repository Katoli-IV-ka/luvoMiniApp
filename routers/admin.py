import logging

from fastapi import APIRouter, HTTPException

from core.config import settings
from import_from_s3 import import_from_s3
from schemas.import_job import (
    ImportFromS3Request,
    ImportFromS3Response,
    ResetDbRequest,
    ResetDbResponse,
)
from utils.drop_db import async_drop_database

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger("uvicorn.error")


@router.post(
    "/import-from-s3",
    response_model=ImportFromS3Response,
    summary="Импорт пользователей из S3 по папке",
)
async def trigger_import_from_s3(payload: ImportFromS3Request) -> ImportFromS3Response:
    if not payload.folder.strip():
        raise HTTPException(status_code=400, detail="Название папки не может быть пустым")

    if not settings.IMPORT_FROM_S3_PASSWORD:
        logger.warning("Попытка импорта при не настроенном IMPORT_FROM_S3_PASSWORD")
        raise HTTPException(status_code=503, detail="Пароль для импорта не настроен")

    if payload.password != settings.IMPORT_FROM_S3_PASSWORD:
        raise HTTPException(status_code=403, detail="Неверный пароль")

    normalized_folder = payload.folder.strip("/")
    try:
        imported = await import_from_s3(prefix=normalized_folder)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Импорт из S3 завершился ошибкой: %s", exc)
        raise HTTPException(status_code=500, detail="Не удалось выполнить импорт") from exc

    return ImportFromS3Response(folder=normalized_folder, imported=imported)


@router.post(
    "/reset-db",
    response_model=ResetDbResponse,
    summary="Очистить базу (drop schema) и пересоздать таблицы",
)
async def reset_db(payload: ResetDbRequest) -> ResetDbResponse:
    if not settings.IMPORT_FROM_S3_PASSWORD:
        logger.warning("Попытка очистки БД при не настроенном IMPORT_FROM_S3_PASSWORD")
        raise HTTPException(status_code=503, detail="Пароль для админ-операций не настроен")

    if payload.password != settings.IMPORT_FROM_S3_PASSWORD:
        raise HTTPException(status_code=403, detail="Неверный пароль")

    try:
        await async_drop_database()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Очистка БД завершилась ошибкой: %s", exc)
        raise HTTPException(status_code=500, detail="Не удалось очистить базу") from exc

    return ResetDbResponse(status="ok")
