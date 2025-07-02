import asyncio
import random
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal
from models.user import User
from models.profile import Profile
from models.photo import Photo

# Список из 100+ S3-ключей, предоставленный вами
S3_KEYS  = [
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


# Заданные имена и даты рождения для примера (19 пользователей)
SAMPLE_USERS = [
    {"first_name": "Alice",  "birthdate": date(1990, 5, 1),  "gender": "female", "about": "Hello, I'm Alice!"},
    {"first_name": "Bob",    "birthdate": date(1988, 8, 12), "gender": "male",   "about": "Hey there, I'm Bob."},
    {"first_name": "Cathy",  "birthdate": date(1992, 3, 7),  "gender": "female", "about": "Artist and traveler."},
    {"first_name": "David",  "birthdate": date(1991, 11, 22),"gender": "male",   "about": "Tech enthusiast."},
    {"first_name": "Emma",   "birthdate": date(1993, 2, 14), "gender": "female", "about": "Book lover."},
    {"first_name": "Frank",  "birthdate": date(1987, 7, 30), "gender": "male",   "about": "Avid cyclist."},
    {"first_name": "Grace",  "birthdate": date(1994, 9, 9),  "gender": "female", "about": "Music is life."},
    {"first_name": "Henry",  "birthdate": date(1989, 4, 18), "gender": "male",   "about": "Coffee addict."},
    {"first_name": "Irene",  "birthdate": date(1995, 1, 25), "gender": "female", "about": "Nature photographer."},
    {"first_name": "Jack",   "birthdate": date(1991, 10, 10),"gender": "male",   "about": "Gamer and coder."},
    {"first_name": "Karen",  "birthdate": date(1992, 12, 5), "gender": "female", "about": "Yoga instructor."},
    {"first_name": "Leo",    "birthdate": date(1986, 6, 6),  "gender": "male",   "about": "Chef in the making."},
    {"first_name": "Mia",    "birthdate": date(1993, 8, 20), "gender": "female", "about": "Travel blogger."},
    {"first_name": "Noah",   "birthdate": date(1988, 2, 28), "gender": "male",   "about": "Movie buff."},
    {"first_name": "Olivia","birthdate": date(1990, 7, 7),  "gender": "female", "about": "Fitness freak."},
    {"first_name": "Paul",   "birthdate": date(1989, 3, 3),  "gender": "male",   "about": "Musician."},
    {"first_name": "Quinn",  "birthdate": date(1994, 5, 15), "gender": "female", "about": "Tattoo artist."},
    {"first_name": "Rachel","birthdate": date(1991, 9, 9),  "gender": "female", "about": "Blogger and designer."},
    {"first_name": "Steve",  "birthdate": date(1987, 12, 12),"gender": "male",   "about": "Adventure seeker."},
    {"first_name": "Tom",    "birthdate": date(1990, 1, 1),  "gender": "male",   "about": "Road trip lover."},
    {"first_name": "Uma",    "birthdate": date(1992, 4, 4),  "gender": "female", "about": "Coffee shop hopper."},
    {"first_name": "Victor","birthdate": date(1985, 5, 5),  "gender": "male",   "about": "History buff."},
    {"first_name": "Wendy", "birthdate": date(1993, 6, 6),  "gender": "female", "about": "Outdoor enthusiast."},
    {"first_name": "Xavier","birthdate": date(1988, 7, 7),  "gender": "male",   "about": "Tech blogger."},
    {"first_name": "Yara",   "birthdate": date(1994, 8, 8),  "gender": "female", "about": "Yoga and meditation."},
    {"first_name": "Zack",   "birthdate": date(1991, 9, 9),  "gender": "male",   "about": "Video editor."},
    {"first_name": "Anna",   "birthdate": date(1990, 10, 10),"gender": "female", "about": "Photographer."},
    {"first_name": "Ben",    "birthdate": date(1989, 11, 11),"gender": "male",   "about": "Fitness coach."},
    {"first_name": "Cara",   "birthdate": date(1992, 12, 12),"gender": "female", "about": "Graphic designer."},
    {"first_name": "Derek",  "birthdate": date(1987, 3, 3),  "gender": "male",   "about": "Guitarist."},
    {"first_name": "Ella",   "birthdate": date(1993, 2, 2),  "gender": "female", "about": "Chef."},
    {"first_name": "Felix",  "birthdate": date(1991, 4, 4),  "gender": "male",   "about": "Writer."},
    {"first_name": "Gina",   "birthdate": date(1994, 5, 5),  "gender": "female", "about": "Musician."},
    {"first_name": "Hugo",   "birthdate": date(1988, 6, 6),  "gender": "male",   "about": "Photographer."},
    {"first_name": "Ivy",    "birthdate": date(1992, 7, 7),  "gender": "female", "about": "Artist."},
    {"first_name": "Kevin","birthdate": date(1990, 8, 8),   "gender": "male",   "about": "Entrepreneur."},
    {"first_name": "Linda","birthdate": date(1989, 9, 9),   "gender": "female", "about": "Teacher."},
    {"first_name": "Mike",   "birthdate": date(1991, 10, 10),"gender": "male",   "about": "Blogger."},
    {"first_name": "Nina",   "birthdate": date(1993, 11, 11),"gender": "female", "about": "Chef."},
    {"first_name": "Oscar",  "birthdate": date(1992, 12, 1), "gender": "male",   "about": "Startup founder."},
]

async def seed():
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        for idx, data in enumerate(SAMPLE_USERS, start=1):
            print(f"SEED: Process...\titem:{idx}")

            # 1) Создаём пользователя
            user = User(
                telegram_user_id=100_000 + idx,
                is_premium=False
            )
            session.add(user)
            await session.flush()  # чтобы получить user.id

            # 2) Создаём профиль
            telegram_un = f"{data['first_name'].lower()}{idx}"
            instagram_un = f"{data['first_name'].lower()}_insta{idx}"
            profile = Profile(
                user_id=user.id,
                first_name=data["first_name"],
                birthdate=data["birthdate"],
                gender=data["gender"],
                about=data["about"],
                telegram_username=telegram_un,
                instagram_username=instagram_un,
            )
            session.add(profile)
            await session.flush()  # чтобы получить profile.id

            # 3) Привязываем от 1 до 6 случайных S3-ключей
            count = random.randint(1, 6)
            chosen_keys = random.sample(S3_KEYS, count)
            for s3_key in chosen_keys:
                photo = Photo(
                    profile_id=profile.id,
                    s3_key=s3_key,
                    is_active=True
                )
                session.add(photo)

        # 4) Финальный коммит всех изменений
        await session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())

