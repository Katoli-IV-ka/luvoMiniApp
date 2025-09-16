from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from core.config import settings

APP_LINK = "https://app.luvo.by/likes"

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Открыть Luvo", web_app=WebAppInfo(url=APP_LINK)
            )
        ]
    ]
)


@dp.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    text = (
        "Привет! 👋 Добро пожаловать в приложение для знакомств Luvo — "
        "мы помогаем найти новые знакомства по твоим подпискам в Instagram. "
        "Чтобы начать знакомиться, запусти приложение! 💫"
    )
    await message.answer(text, reply_markup=main_keyboard)


async def send_like_notification(chat_id: int) -> None:
    await bot.send_message(
        chat_id,
        "Кому-то понравился твой профиль ❤️ Узнай, кто это",
        reply_markup=main_keyboard,
    )

async def send_match_notification(chat_id: int) -> None:
    await bot.send_message(
        chat_id,
        "Совпадение! 🔥 У вас взаимный интерес — начни общение",
        reply_markup=main_keyboard,
    )


async def start_bot() -> None:
    await dp.start_polling(bot)