import asyncio
import random
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal
from models.user import User
from models.profile import Profile
from models.photo import Photo

# Список из 100+ S3-ключей, предоставленный вами
S3_KEYS = [
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_1_97ce2548ec41463f9a8ce2a228691128.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_10_8aa8233b090e4d89be4df6354a486aef.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_11_2da0926ccfcf41f4b66b9aca0785068f.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_12_f097692b11dc4e85b9a98b1f3bbe6a6e.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_13_7ec26eb38de949c884b3430bcb8387d2.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_14_69025c3de4b149308f883795880caaf2.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_15_2eb255e4722e4b71abae8a25063d062a.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_16_acc98ab42f5847e29125aff7d2d5d4b3.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_17_1e6c5fb7bb5847698fc08c301b3e4318.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_18_2f5107c60b554241abcdc2cc627af7bd.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_19_9cab0028f2c84ebfb8e1f99ddcca10f0.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_2_b547a112919f4b338b851a7aaadfaeec.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_3_85632630433647fe9f4a79393a7907a1.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_4_c9d729f7c777451384663fa5e2a2b9e1.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_5_5e49cc3f7cac456d97b15468fe4a8045.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_6_6deba5cc03144f49929099e561930d28.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_7_c341df862da74bfb85b42581601b6b15.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_8_bb807f60325d4157b16d712c02d34c9e.png",
    "s3.twcstorage.ru/50d41739-luvo-backet/profiles/img_9_c73dd3311ee2457da26185d14a1aab9b.png",
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

