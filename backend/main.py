DATABASE_URL = "postgresql+asyncpg://postgres:ваш_пароль@localhost/dating_app"

import asyncpg

async def test_connection():
    conn = await asyncpg.connect(
        user='postgres',
        password='94044024p',
        database='luvoMiniApp',
        host='localhost'
    )
    print("Подключение успешно!")
    await conn.close()

import asyncio
asyncio.run(test_connection())