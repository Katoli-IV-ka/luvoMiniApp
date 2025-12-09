from pydantic import BaseModel, Field


class ImportFromS3Request(BaseModel):
    folder: str = Field(..., description="Название папки (prefix) с фото в S3")
    password: str = Field(..., description="Пароль для запуска импорта")


class ImportFromS3Response(BaseModel):
    folder: str
    imported: int


class ResetDbRequest(BaseModel):
    password: str


class ResetDbResponse(BaseModel):
    status: str
