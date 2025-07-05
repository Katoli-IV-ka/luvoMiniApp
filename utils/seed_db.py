# backend/utils/seed_db.py
import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy import select

from core.database import AsyncSessionLocal
from core.id_generator import generate_random_id
from models.user import User
from models.photo import Photo
from models.like import Like
from models.match import Match
from models.feed_view import FeedView

# Константы для семплов
NUM_USERS = 20
MAX_PHOTOS_PER_USER = 5
NUM_LIKES = 50
NUM_VIEWS = 60
NUM_MATCHES = 10

# Пример рандомных имен
FIRST_NAMES = [
    "Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Jamie", "Reese", "Drew", "Quinn",
    "Riley", "Avery", "Cameron", "Logan", "Hayden", "Peyton", "Skyler", "Dakota", "Emerson", "Kai"
]
GENDERS = ["male", "female", "other"]
ABOUT_TEMPLATES = [
    "Love hiking and outdoor adventures.",
    "Coffee fanatic and book lover.",
    "Tech enthusiast and amateur chef.",
    "Travel addict exploring the world.",
    "Music is life. Always at concerts.",
]

# Фиксированный список ключей S3 для фото
S3_KEYS = [
    "profiles/img_1_4e14f58aa10a4d86b53cd3c1e814ba7c.jpg",
    "profiles/img_10_875b47e0d0ac4fc3908025e40b1aa388.jpg",
    "profiles/img_11_808ef7cb0df74ea289df21699576dbc5.jpg",
    "profiles/img_12_a756e645c6d24df6a3f66b6347de7df8.jpg",
    "profiles/img_13_e0d4a492a8c444149daf27e27455d9ba.jpg",
    "profiles/img_14_bad1363c96e04d65aabce3e3cb67b172.jpg",
    "profiles/img_15_9810f6e5c1ca4585bf075f0b7c0e024d.jpg",
    "profiles/img_16_35c98b74ea39456fb1ba7b710337e6bc.jpg",
    "profiles/img_17_ae8553dd7fea4ed8abaeb3b172cd6eb7.jpg",
    "profiles/img_18_15d069f425554f019f41687caeaacd00.jpg",
    "profiles/img_19_aa1f3e9cd38448c39aa94c8c7b56d527.jpg",
    "profiles/img_2_4e234ade1f984facaf8ec705d65b7a20.jpg",
    "profiles/img_20_3f14bcb8fea54fca9b5a933f4ebb9759.jpg",
    "profiles/img_3_c93f8835526a40efb97ebd975b51c57a.jpg",
    "profiles/img_4_e5b75fe863344828a00dfa72434bb9ac.jpg",
    "profiles/img_5_329181a6aff4474cae446a6c50245bd2.jpg",
    "profiles/img_6_300559b4fc2a444fa167feb06b25a543.jpg",
    "profiles/img_7_22aac45bae93495b91e14450c5a44d30.jpg",
    "profiles/img_8_a145dea7fe39465a95b9ea5dbbdb95d4.jpg",
    "profiles/img_9_488edbdae5b743f284ad394066fd129c.jpg",
]

async def seed():
    # Инициализация БД (создание схем)
    async with AsyncSessionLocal() as session:
        users = []
        for _ in range(NUM_USERS):
            uid = generate_random_id('user')
            user = User(
                id=uid,
                telegram_user_id=random.randint(100000, 999999),
                first_name=random.choice(FIRST_NAMES),
                birthdate=datetime.utcnow().date() - timedelta(days=random.randint(18*365, 45*365)),
                gender=random.choice(GENDERS),
                about=random.choice(ABOUT_TEMPLATES),
                latitude=round(random.uniform(-90, 90), 6),
                longitude=round(random.uniform(-180, 180), 6),
                telegram_username=f'user{uid}',
                instagram_username=f'inst{uid}',
                is_premium=random.choice([False, True]),
                premium_expires_at=(datetime.utcnow() + timedelta(days=30)) if random.random() < 0.2 else None,
                created_at=datetime.utcnow()
            )
            session.add(user)
            users.append(user)
        await session.commit()

        # 2. Добавляем фото к каждому пользователю из фиксированного списка
        for user in users:
            count = random.randint(1, min(MAX_PHOTOS_PER_USER, len(S3_KEYS)))
            keys = random.sample(S3_KEYS, count)
            for i, s3_key in enumerate(keys):
                pid = generate_random_id('photo')
                photo = Photo(
                    id=pid,
                    user_id=user.id,
                    s3_key=s3_key,
                    is_general=(i == 0),
                    created_at=datetime.utcnow()
                )
                session.add(photo)
        await session.commit()

        # 3. Генерируем лайки
        all_ids = [u.id for u in users]
        for _ in range(NUM_LIKES):
            liker, liked = random.sample(all_ids, 2)
            exists = await session.execute(
                select(Like).where(Like.liker_id == liker, Like.liked_id == liked)
            )
            if exists.scalar_one_or_none():
                continue
            lid = generate_random_id('like')
            like = Like(id=lid, liker_id=liker, liked_id=liked, created_at=datetime.utcnow())
            session.add(like)
        await session.commit()

        # 4. Создаем матчи из взаимных лайков
        likes = (await session.execute(select(Like))).scalars().all()
        pairs = set()
        for l in likes:
            for r in likes:
                if l.liker_id == r.liked_id and l.liked_id == r.liker_id:
                    pair = tuple(sorted((l.liker_id, l.liked_id)))
                    pairs.add(pair)
        for u1, u2 in list(pairs)[:NUM_MATCHES]:
            mid = generate_random_id('match')
            match = Match(id=mid, user1_id=u1, user2_id=u2, created_at=datetime.utcnow())
            session.add(match)
        await session.commit()

        # 5. Генерируем просмотры
        for _ in range(NUM_VIEWS):
            viewer, viewed = random.sample(all_ids, 2)
            vid = generate_random_id('feed_view')
            view = FeedView(id=vid, viewer_id=viewer, viewed_id=viewed, created_at=datetime.utcnow())
            session.add(view)
        await session.commit()

    print("✅ DB seeded successfully")

if __name__ == '__main__':
    asyncio.run(seed())
