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
    "profiles/72_545c8fddbc294bb8b788773777e5ac4a_cca779d4b5bc47deb66b45c2fcef6279.jpg",
    "profiles/72_24db00d7fbc240a39a886dab5f945225_0b986a450a2547e386127944e912dd3f.jpg",
    "profiles/73_9272c34450ce467083eb3f9b2cc57b63_4f56b9f27f11428d9a541ff5f705a2a4.jpg",
    "profiles/lena_cook_1.png_aca02cb0ba6c47048b51baef0ff7f64c.jpg",
    "profiles/anna_art_4.png_fc276667987a4902a4b2f42d8510c85c.jpg",
    "profiles/victor_travel_1.png_d580fb9728fa406a99867b74e3cd3568.jpg",
    "profiles/73_fe9e0d71da9e42c4a7b7a0c8e897309b_647e6b76e62843ab90ba8103152f2651.jpg",
    "profiles/74_7f60b9cae51f4fe680630f9420a5889e_07ce5b5c6666499587d5feb560b551f4.jpg",
    "profiles/74_9c7d12bf1d284dea83a6bee557e4f600_431e47a023ef4b2fb9f90bbb17d2791f.jpg",
    "profiles/74_b07a8f39237144d1b7de987ec872f118_490b9a58b01343778d164da4a2462bb0.jpg",
    "profiles/74_5f43c195ca614042af57fd50f468ca65_34497a9983fe421dba533b3ef3b99cd3.jpg",
    "profiles/74_b1eaab622537401291fea1786d810017_714d11583ab64d739bb84e48251320f9.jpg",
    "profiles/74_43c25adb65544595833171bdb6e667b2_eb603d7f36b2457b89bcc67b1f891073.jpg",
    "profiles/75_be797a39b50047cd8ff415f6a1ef6d95_abb5d8d470b741339fa0ffc40ba6efc4.jpg",
    "profiles/75_8f9bb18f7cc24e1ab53f5e0f5f3f7999_c30178ead304494c8d7ec830caaabcc8.jpg",
    "profiles/75_6eb811f2971243edb91365f8cb797535_dd89165948ee49e0a461b054b20a2b1c.jpg",
    "profiles/75_991f28f61c0f4716ab3c8b09b1034ad4_852984fad2364209ae4fa0f568fecf6b.jpg",
    "profiles/76_cf6c97ceff764bf890c20077c17e6b95_ae84c05b35f248999e37a80223dbb025.jpg",
    "profiles/76_ea659ee93d7a41c2bb0fac2f74c3b678_f0f96c5bdac749c7b77e97c237245436.jpg",
    "profiles/77_c701a76d5b8b45528b6ad1d8db819309_02aaee02ff1c495eb9eda67a24f6339a.jpg",
    "profiles/77_b5c32d9cc2264ef488aa2cfa539f5e3d_884878182ee24f438495d3ef055323c7.jpg",
    "profiles/77_c71b8869090f4edba441dc47a84db752_a8d77f14bfcb42d2bbb8fd9a92290947.jpg",
    "profiles/77_47c79bb6fe524870b7af8c283ab88e14_ae7d74e4a61345998df30dfd16c5d4f3.jpg",
    "profiles/78_e022e9d1c44f40d5b1602389a0726436_1bfd16c28fdc4c2d8250cda7426a87d9.jpg",
    "profiles/78_a8300600b7af4ef48007ada22b4ccb77_05258e8e933245679380becd552af7b7.jpg",
    "profiles/78_5c753c861b594ff89eef9805c737a460_7a840b8bc0334b9e9ce6758e64b52c51.jpg",
    "profiles/78_0bc2c60b8406421eb56a5d1cd527ac5c_2ef067782e934de69b2c382db51bebab.jpg",
    "profiles/79_95aa8ec8cd604dcbb39552fc47075f35_6fe5fa944363486eae2c8fd71eaaa52a.jpg",
    "profiles/80_f98c3c97f7be4188856359511b1776fd_20be544963374acebe316d068013c79c.jpg",
    "profiles/80_448280f300ef4116b27f027f5f488cb6_8561ee7c0ebf44b2a573c3884f67a5de.jpg",
    "profiles/81_d98b4ae003cc4400af57f6035727fa6d_f86fd204a3014556b260e3ae84259720.jpg",
    "profiles/81_76251b13e2e64bc388f1a2c23e6f80f6_e743a5f16ca248c48f7e8f41844a2807.jpg",
    "profiles/81_b584f2ea3ca540b0969365fab6b3e529_d94572df0a2047bcb430810dfc9229bf.jpg",
    "profiles/81_be1f04e86bea4296928ae4194ed52f82_69a74108f6c84c029c1bb371769aa016.jpg",
    "profiles/82_97de1ab7fb61473d8b6eabdb2ffb0520_a0d123fe48bb4bb89f46c3ec70a19341.jpg",
    "profiles/83_f0d9dfc1086a4896abe1cf7089d977c0_0604659df01441119a355b29ef8523bf.jpg",
    "profiles/83_cad690e9c5ef4ff19adc295b4cb0b1ab_703a7af1a1a5447da8836965081e0adc.jpg",
    "profiles/84_c9e1b11754bf442b8af07cd48043b716_484458311ac1422b9122a8787b16000c.jpg",
    "profiles/84_d3725f3fac6246ce9837fc971aa7ca38_17b43656151041129a3ff2327ac6aed3.jpg",
    "profiles/84_3daabef71ca0444bb186acc361f39faf_331a4acc857e4ee09f0cae2cbac3d2ee.jpg",
    "profiles/71_26520080bee94b18b6b360f9fce9f69b_835bea9e84d94795b866406870b4bbc1.jpg",
    "profiles/85_706e075bb62a4637977f3a40b0ab9935_bd645bb822824adbaa5997979909be9a.jpg",
    "profiles/85_fb8930ab800047378a7cdfec17208619_18639b9975654f938d414c2e1ddabad2.jpg",
    "profiles/85_d7bc308a0fd0473aa1ac2cf03fd4a9d2_ed278c44feb84b8d9a8de1a91b56456d.jpg",
    "profiles/85_e8ba64f9da87427a8791ac025449434d_cc9e56e6b2fd45bda14d5c2d9b69cd32.jpg",
    "profiles/85_2124961b73874558a2989effa5aa18b0_482fa560cf1942de8c1abfbfa0f860c3.jpg",
    "profiles/86_45cb6903ba3b470d9c88c533f78e1a2a_69f0de5e3c364f2985e70f24dc947c6e.jpg",
    "profiles/87_78537f2ff11a455e924a190fd21e2164_eaa84c8530174eca80c95a1e838f29ce.jpg",
    "profiles/87_3334cfa743b3458cbec37ab0abdb3ee0_b3ab12b3eadc4a61bef52ff3306092b1.jpg",
    "profiles/87_5a557e03b53b490098097b3c3557b504_d47ff650ce174eadb3fa84a1559a1534.jpg",
    "profiles/88_a0fe567a530d41658589129cfec16842_55b5c7c0dd254652be0d662044e2eb9d.jpg",
    "profiles/88_d19a0b3584694265abc1f1401f3af1df_21e8e3a2e9f24636aec1398c5f783db2.jpg",
    "profiles/89_7f7e032c313940b0a2004f47b6519877_8f1d44763a33432683dbf1762f545cf4.jpg",
    "profiles/89_7f9c4d5ef9874e768fc261a0f58f87a1_e995780a0c354f359791946096159557.jpg",
    "profiles/89_8a98b05449fd43a2be3b0d43d3028c07_706f1619883946d583db5b797ddb3d53.jpg",
    "profiles/89_28647d36f0a24856bcaf6e8258ca0d7b_527f7eb692a5466bb818d7847f43011b.jpg",
    "profiles/89_1578166e225a405bb07f2df88343ed89_92faf710f843419baeeda174a4d82eef.jpg",
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

