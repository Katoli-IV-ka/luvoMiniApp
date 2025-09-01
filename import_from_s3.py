import asyncio
import random
import string
from datetime import datetime, timedelta, date, timezone
from itertools import cycle


import boto3

from core.config import settings
from core.database import AsyncSessionLocal
from core.id_generator import generate_random_id
from models.user import User
from models.photo import Photo

# Сырой список имён из задания
RAW_NAMES = [
    "Соня", "Маша", "Аня", "Настя", "Вика", "Лиза", "Даша", "Варя", "Саша", "Мила",
    "Ксюш", "Вика", "Валя", "Люда", "Алёна", "Ника", "Надя", "Зоя", "Злата", "Белла",
    "Нелли", "КАРИНА", "Виолетта", "Эрика", "Ася", "Рада", "Алиса", "Анастасия", "Анна", "Полина",
    "Виктория", "Дарья", "Ева", "Эмилия", "Злата", "Мария", "Дашкас", "Машкас", "Дина", "ЮЛЯ",
    "Маша", "Аня", "Настя", "Катя", "Оля", "Лена", "Таня", "МАША", "Наташа", "УЛЬЯНА",
    "маша", "Валя", "Надя", "Галя", "Вера", "Лара", "ева", "нина", "Дашариус", "Мария",
    "Стефа", "Вероника", "Рита", "Валентина", "Ритуся", "Натусик", "Нара", "Эльза", "Вита", "Крис",
    "Ками", "Амира", "Оксана", "Валерия", "Валери", "Маша", "Аня", "Катя", "Оля", "Лена",
    "ВАЛЯ", "Ира", "Наташа", "Света", "Маруся", "МАРУСЯ", "Василиса", "Марина", "МАРИЯ"
]

def clean_names(names):
    seen = set()
    result = []
    for name in names:
        cleaned = name.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned.title())
    return result

NAMES = clean_names(RAW_NAMES)
ABOUT_TEMPLATES = ["😊", "🚀", "🎨", "🎶", "☕", "📚", "Путешествую", "Люблю кофе", "🌟", "😎"]


def random_username(prefix: str) -> str:
    chars = string.ascii_letters + string.digits + "_"
    return prefix + ''.join(random.choice(chars) for _ in range(8))


async def import_from_s3(bucket: str = settings.AWS_S3_BUCKET_NAME, prefix: str = "demos") -> None:
    session = boto3.session.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
    )
    s3 = session.client("s3", endpoint_url=settings.AWS_S3_ENDPOINT_URL)

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    keys: list[str] = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Только верхний уровень
            if "demos/" in key[len(prefix):]:
                continue
            keys.append(key)
    if not keys:
        print("Нет файлов для импорта")
        return

    name_cycle = cycle(NAMES)
    today = date.today()

    async with AsyncSessionLocal() as db:
        for key in keys:
            uid = generate_random_id("users")
            first_name = next(name_cycle)
            birthdate = today - timedelta(days=random.randint(17 * 365, 22 * 365))
            about = random.choice(ABOUT_TEMPLATES) if random.random() < 0.4 else None

            user = User(
                id=uid,
                telegram_user_id=random.randint(100_000, 999_999),
                first_name=first_name,
                birthdate=birthdate,
                gender="female",
                about=about,
                telegram_username=random_username("tg_"),
                instagram_username=random_username("inst_"),
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)

            pid = generate_random_id("photos")
            photo = Photo(
                id=pid,
                user_id=uid,
                s3_key=key,
                is_general=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(photo)

        await db.commit()
    print(f"Импортировано пользователей: {len(keys)}")


if __name__ == "__main__":
    asyncio.run(import_from_s3())