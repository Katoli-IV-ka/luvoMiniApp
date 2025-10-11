
import asyncio
import html
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramAPIError

from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiohttp import ClientError, ClientSession
from sqlalchemy import delete, or_, select

from core.config import settings
from core.database import AsyncSessionLocal
from models.battle import Battle
from models.feed_view import FeedView
from models.instagram_connection import InstagramConnection
from models.instagram_data import InstagramData
from models.like import Like
from models.match import Match
from models.photo import Photo
from models.user import User

APP_BASE_LINK = "https://vitalycatt-luvo-mini-app-da35.twc1.net"
LIKES_LINK = f"{APP_BASE_LINK}/likes"
FEED_LINK = f"{APP_BASE_LINK}/feed"
CREATE_ACCOUNT_LINK = f"{APP_BASE_LINK}/onboarding"
EDIT_PROFILE_LINK = f"{APP_BASE_LINK}/profile/edit"

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

logger = logging.getLogger(__name__)


_review_message_bases: dict[tuple[int, int], str] = {}


def _message_key(message: types.Message) -> Optional[tuple[int, int]]:
    if not message.chat:
        return None
    return (message.chat.id, message.message_id)


def _remember_review_caption(
    message: types.Message, caption: str, *, overwrite: bool = False
) -> None:
    key = _message_key(message)
    if key is None:
        return
    if overwrite or key not in _review_message_bases:
        _review_message_bases[key] = caption


def _get_review_caption(message: types.Message) -> Optional[str]:
    key = _message_key(message)
    if key is None:
        return None
    return _review_message_bases.get(key)


def _forget_review_caption(message: types.Message) -> None:
    key = _message_key(message)
    if key is None:
        return
    _review_message_bases.pop(key, None)


def build_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Luvo", web_app=WebAppInfo(url=url)
                )
            ]
        ]
    )


feed_keyboard = build_keyboard(FEED_LINK)
likes_keyboard = build_keyboard(LIKES_LINK)


@dataclass
class UserProfileSnapshot:
    user_id: int
    telegram_user_id: int
    first_name: Optional[str]
    birthdate: Optional[date]
    about: Optional[str]
    telegram_username: Optional[str]
    instagram_username: Optional[str]


OPTION_HIDE_PHOTO = 1
OPTION_HIDE_NAME = 2
OPTION_HIDE_BIO = 4
OPTION_ORDER = (OPTION_HIDE_PHOTO, OPTION_HIDE_NAME, OPTION_HIDE_BIO)

OPTION_BUTTON_LABELS = {
    OPTION_HIDE_PHOTO: "скрыть фото",
    OPTION_HIDE_NAME: "скрыть имя",
    OPTION_HIDE_BIO: "скрыть bio",
}

OPTION_ACTION_LABELS = {
    OPTION_HIDE_PHOTO: "скрыто фото",
    OPTION_HIDE_NAME: "скрыто имя",
    OPTION_HIDE_BIO: "скрыто bio",
}

OPTION_NOTIFICATION_LINES = {
    OPTION_HIDE_PHOTO: "✨ Часть твоих фотографий",
    OPTION_HIDE_NAME: "✨ Твоё имя",
    OPTION_HIDE_BIO: "✨ Информацию в разделе «О себе»",
}

BLOCK_NOTIFICATION_TEXT = (
    "Привет! 😊\n\n"
    "Твой предыдущий аккаунт был отключён из-за нарушения правил сообщества. "
    "Это не навсегда — ты можешь создать новый и начать всё с чистого листа.\n\n"
    "Прежде чем зарегистрироваться, используй команду /rule, чтобы ознакомиться с "
    "правилами нашего сообщества. Мы очень хотим, чтобы ты остался с нами, и чтобы "
    "у тебя больше не было неприятных ситуаций."
)

COMMUNITY_RULES_TEXT = (
    "<b>Правила сообщества: вместе создадим безопасное пространство</b>\n\n"
    "Добро пожаловать в наше сообщество! Наша главная цель — создать "
    "доброжелательную и комфортную атмосферу для всех.\n\n"
    "<b>📷 Ваш профиль: фотографии</b>\n"
    "• Четкие и качественные фотографии, где вас хорошо видно\n"
    "• Ваши настоящие фото\n\n"
    "<b>❌ Что запрещено:</b>\n"
    "• Контент для взрослых (18+)\n"
    "• Деструктивный контент\n"
    "• Фотографии других людей без согласия\n"
    "• Политическая и коммерческая агитация\n\n"
    "<b>👤 Ваше имя</b>\n"
    "• Реальное имя (Мария, Александр)\n"
    "• Имя, под которым вас знают друзья\n\n"
    "<b>❌ Что запрещено:</b>\n"
    "• Обезличенные ники (Кот_007, Аноним)\n"
    "• Имена с рекламой или оскорблениями\n\n"
    "<b>📝 Ваша анкета (Bio)</b>\n"
    "• Доброжелательный рассказ о ваших увлечениях\n\n"
    "<b>❌ Что запрещено:</b>\n"
    "• Оскорбления и дискриминационные высказывания\n"
    "• Разжигание ненависти\n"
    "• Запрещенный контент\n\n"
    "<b>Важно:</b> Профили, нарушающие эти правила, будут заблокированы.\n\n"
    "Спасибо, что помогаете нам строить сообщество, основанное на уважении и доверии! 🤝"
)


def _calculate_age(birthdate: Optional[date]) -> Optional[int]:
    if not birthdate:
        return None
    today = date.today()
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return max(years, 0)


def _escape(text: Optional[str], default: str = "—") -> str:
    if not text:
        return default
    return html.escape(text)


def _build_profile_caption(snapshot: UserProfileSnapshot) -> str:
    first_name = _escape(snapshot.first_name)
    age = _calculate_age(snapshot.birthdate)
    age_part = f"{age} лет" if age is not None else "— лет"
    tg_username = (
        f"@{snapshot.telegram_username}" if snapshot.telegram_username else "—"
    )
    instagram = _escape(snapshot.instagram_username)

    lines = [
        f"👤<b>{first_name}</b>, {age_part}",
        "",
        f"tg: {tg_username}",
        f"inst: {instagram}",
    ]

    about_text = (snapshot.about or "").strip()
    if about_text:
        lines.extend(["", f"✏️ Bio: <i>{html.escape(about_text)}</i>"])

    return "\n".join(lines)


def _compose_caption(base_caption: str, status_line: Optional[str]) -> str:
    if status_line:
        return f"{status_line}\n\n{base_caption}"
    return base_caption


def _format_selected_options_line(flags: int) -> str:
    selected = [OPTION_BUTTON_LABELS[opt] for opt in OPTION_ORDER if flags & opt]
    if not selected:
        return "Выбраны опции: нет"
    return "Выбраны опции: " + ", ".join(selected)


def _format_result_line(
    is_approved: bool, action_flags: list[int], admin_username: str
) -> str | None:
    if not is_approved:
        return f"🚫: {admin_username}"

    status_symbol = "✅"
    performed_labels = [
        OPTION_ACTION_LABELS[flag]
        for flag in OPTION_ORDER
        if flag in action_flags
    ]

    if performed_labels:
        actions = "/".join(performed_labels)
        return f"{status_symbol} [{actions}]: {admin_username}"
    else:
        return f"{status_symbol}: {admin_username}"


def _admin_username(user: types.User) -> str:
    if user.username:
        return f"@{user.username}"
    return f"id{user.id}"


def _build_keyboard(user_id: int, flags: int) -> InlineKeyboardMarkup:
    def option_text(option_flag: int) -> str:
        label = OPTION_BUTTON_LABELS[option_flag]
        return ("➕ " + label) if (flags & option_flag) else label

    keyboard = [
        [
            InlineKeyboardButton(
                text="✅",
                callback_data=f"regapprove:{user_id}:{flags}",
            ),
            InlineKeyboardButton(
                text="🚫",
                callback_data=f"regdecline:{user_id}:{flags}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=option_text(OPTION_HIDE_PHOTO),
                callback_data=f"regopt:{user_id}:{flags}:{OPTION_HIDE_PHOTO}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=option_text(OPTION_HIDE_NAME),
                callback_data=f"regopt:{user_id}:{flags}:{OPTION_HIDE_NAME}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=option_text(OPTION_HIDE_BIO),
                callback_data=f"regopt:{user_id}:{flags}:{OPTION_HIDE_BIO}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _fetch_snapshot(session, user_id: int) -> Optional[UserProfileSnapshot]:
    user = await session.get(User, user_id)
    if not user:
        return None
    return UserProfileSnapshot(
        user_id=user.id,
        telegram_user_id=user.telegram_user_id,
        first_name=user.first_name,
        birthdate=user.birthdate,
        about=user.about,
        telegram_username=user.telegram_username,
        instagram_username=user.instagram_username,
    )


async def _get_general_photo_url(session, user_id: int) -> Optional[str]:
    result = await session.execute(
        select(Photo)
        .where(Photo.user_id == user_id)
        .order_by(Photo.is_general.desc(), Photo.created_at.asc())
    )
    photo = result.scalars().first()
    if not photo:
        return None
    return f"{settings.s3_base_url}/{photo.s3_key}"


async def _download_photo(photo_url: str) -> Optional[BufferedInputFile]:
    try:
        async with ClientSession() as session:
            async with session.get(photo_url, timeout=10) as response:
                response.raise_for_status()
                content = await response.read()
    except (ClientError, asyncio.TimeoutError) as exc:
        logger.warning(
            "Failed to download photo %s for admin review: %s",
            photo_url,
            exc,
            exc_info=exc,
        )
        return None

    if not content:
        return None

    return BufferedInputFile(content, filename="profile.jpg")


def _placeholder_photo_url() -> str:
    return f"{settings.s3_base_url}/{settings.PLACEHOLDER_PHOTO_S3_KEY}"


async def _try_send_admin_photo(
    photo_source: object,
    caption: str,
    keyboard: InlineKeyboardMarkup,
) -> Optional[types.Message]:
    try:
        return await bot.send_photo(
            chat_id=settings.ADMIN_REVIEW_CHAT_ID,
            photo=photo_source,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except TelegramAPIError as exc:
        logger.warning("Failed to send review photo: %s", exc, exc_info=exc)
        return None


async def _send_admin_notification_with_fallback(
    photo_url: Optional[str], caption: str, keyboard: InlineKeyboardMarkup
) -> Optional[types.Message]:
    attempted_urls: list[str] = []
    if photo_url:
        attempted_urls.append(photo_url)

    placeholder_url = _placeholder_photo_url()
    if placeholder_url and placeholder_url not in attempted_urls:
        attempted_urls.append(placeholder_url)

    for url in attempted_urls:
        message = await _try_send_admin_photo(url, caption, keyboard)
        if message:
            return message

        photo_file = await _download_photo(url)
        if photo_file:
            message = await _try_send_admin_photo(photo_file, caption, keyboard)
            if message:
                return message

    try:
        return await bot.send_message(
            chat_id=settings.ADMIN_REVIEW_CHAT_ID,
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except TelegramAPIError as exc:
        logger.exception("Failed to send review notification", exc_info=exc)
        return None


async def _edit_admin_message(
    message: types.Message,
    *,
    caption: str,
    keyboard: Optional[InlineKeyboardMarkup],
) -> bool:
    try:
        if message.photo:
            await message.edit_caption(
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await message.edit_text(
                text=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        return True
    except TelegramAPIError as exc:
        logger.warning("Failed to update admin message: %s", exc, exc_info=exc)
        return False


async def notify_admin_about_new_user(user_id: int) -> None:
    if not settings.ADMIN_REVIEW_CHAT_ID:
        logger.warning("ADMIN_REVIEW_CHAT_ID is not configured")
        return
    async with AsyncSessionLocal() as session:
        snapshot = await _fetch_snapshot(session, user_id)
        if not snapshot:
            logger.warning("User %s not found for review notification", user_id)
            return
        photo_url = await _get_general_photo_url(session, user_id)
        caption = _build_profile_caption(snapshot)
        keyboard = _build_keyboard(user_id, 0)
    message = await _send_admin_notification_with_fallback(
        photo_url, caption, keyboard
    )
    if message:
        _remember_review_caption(message, caption, overwrite=True)


def _build_user_button(text: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]]
    )


async def _send_user_notification(
    telegram_user_id: int,
    text: str,
    *,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "HTML",
) -> None:
    try:
        await bot.send_message(
            chat_id=telegram_user_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "Failed to notify user %s: %s", telegram_user_id, exc, exc_info=exc
        )


def _build_actions_notification(performed_flags: list[int]) -> str:
    lines = [OPTION_NOTIFICATION_LINES[flag] for flag in OPTION_ORDER if flag in performed_flags]
    actions_block = "\n\n".join(lines)
    return (
        "Привет! 😊\n\n"
        "Пока мы проверяли аккаунты, заметили, что твой профиль немного выбивается из "
        "правил нашего сообщества. Поэтому нам пришлось кое-что скрыть:\n\n"
        f"{actions_block}\n\n"
        "Но не переживай! Всё легко исправить.\n\n"
        "Просто зайди в раздел «О себе» и приведи анкету в соответствие с нашими правилами — "
        "тогда всё сразу вернётся на свои места! 🛠️\n\n"
        "Если нужно освежить в памяти правила, просто введи команду <code>/rule</code> — там "
        "всё подробно написано!\n\n"
        "Ждём тебя с обновлённым профилем! 😉"
    )


async def _apply_options(session, snapshot: UserProfileSnapshot, flags: int) -> list[int]:
    performed: list[int] = []
    user = await session.get(User, snapshot.user_id)
    if not user:
        return performed
    if flags & OPTION_HIDE_PHOTO:
        result = await session.execute(select(Photo).where(Photo.user_id == user.id))
        photos = result.scalars().all()
        replaced = False
        for photo in photos:
            if photo.s3_key != settings.PLACEHOLDER_PHOTO_S3_KEY:
                photo.s3_key = settings.PLACEHOLDER_PHOTO_S3_KEY
                replaced = True
        if replaced:
            performed.append(OPTION_HIDE_PHOTO)
    if flags & OPTION_HIDE_NAME:
        if user.first_name != settings.PLACEHOLDER_NAME:
            user.first_name = settings.PLACEHOLDER_NAME
            performed.append(OPTION_HIDE_NAME)
    if flags & OPTION_HIDE_BIO:
        if user.about != settings.PLACEHOLDER_BIO:
            user.about = settings.PLACEHOLDER_BIO
            performed.append(OPTION_HIDE_BIO)
    return performed


async def _delete_user_data(session, user_id: int) -> None:
    await session.execute(delete(Photo).where(Photo.user_id == user_id))
    await session.execute(
        delete(Like).where(or_(Like.liker_id == user_id, Like.liked_id == user_id))
    )
    await session.execute(
        delete(Match).where(or_(Match.user1_id == user_id, Match.user2_id == user_id))
    )
    await session.execute(
        delete(FeedView).where(
            or_(FeedView.viewer_id == user_id, FeedView.viewed_id == user_id)
        )
    )
    await session.execute(
        delete(Battle).where(
            or_(Battle.user_id == user_id, Battle.opponent_id == user_id, Battle.winner_id == user_id)
        )
    )
    await session.execute(delete(InstagramData).where(InstagramData.user_id == user_id))
    await session.execute(delete(InstagramConnection).where(InstagramConnection.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))


@dp.callback_query(F.data.startswith("regopt:"))
async def handle_option_selection(callback: types.CallbackQuery) -> None:
    try:
        _, user_id_str, flags_str, option_str = callback.data.split(":")  # type: ignore[arg-type]
        user_id = int(user_id_str)
        flags = int(flags_str)
        option = int(option_str)
    except (ValueError, AttributeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    if option not in OPTION_ORDER:
        await callback.answer("Неизвестная опция", show_alert=True)
        return

    new_flags = flags ^ option

    async with AsyncSessionLocal() as session:
        snapshot = await _fetch_snapshot(session, user_id)
        if not snapshot:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        base_caption = _build_profile_caption(snapshot)
        _remember_review_caption(callback.message, base_caption, overwrite=True)

    status_line = _format_selected_options_line(new_flags)
    caption = _compose_caption(base_caption, status_line)
    keyboard = _build_keyboard(user_id, new_flags)

    if not await _edit_admin_message(
        callback.message,
        caption=caption,
        keyboard=keyboard,
    ):
        await callback.answer("Не удалось обновить сообщение", show_alert=True)
        return

    await callback.answer("Опции обновлены")


@dp.callback_query(F.data.startswith("regapprove:"))
async def handle_registration_approve(callback: types.CallbackQuery) -> None:
    try:
        _, user_id_str, flags_str = callback.data.split(":")  # type: ignore[arg-type]
        user_id = int(user_id_str)
        flags = int(flags_str)
    except (ValueError, AttributeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        snapshot = await _fetch_snapshot(session, user_id)
        if not snapshot:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        try:
            performed_flags = await _apply_options(session, snapshot, flags)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.exception("Failed to approve registration", exc_info=exc)
            await callback.answer("Не удалось подтвердить регистрацию", show_alert=True)
            return
          
    base_caption = _build_profile_caption(snapshot)
    _remember_review_caption(callback.message, base_caption, overwrite=True)
    admin_name = _admin_username(callback.from_user)
    status_line = _format_result_line(True, performed_flags, admin_name)
    caption = _compose_caption(base_caption, status_line)

    if not await _edit_admin_message(
        callback.message,
        caption=caption,
        keyboard=None,
    ):
        await callback.answer("Не удалось обновить сообщение", show_alert=True)
        return

    if performed_flags:
        notification_text = _build_actions_notification(performed_flags)
        await _send_user_notification(
            snapshot.telegram_user_id,
            notification_text,
            reply_markup=_build_user_button("Редактировать профиль", EDIT_PROFILE_LINK),
        )

    _forget_review_caption(callback.message)
    await callback.answer("Регистрация подтверждена")


@dp.callback_query(F.data.startswith("regdecline:"))
async def handle_registration_decline(callback: types.CallbackQuery) -> None:
    try:
        _, user_id_str, _ = callback.data.split(":")  # type: ignore[arg-type]
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        snapshot = await _fetch_snapshot(session, user_id)
        if not snapshot:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        base_caption = _build_profile_caption(snapshot)
        telegram_user_id = snapshot.telegram_user_id
        try:
            await _delete_user_data(session, user_id)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.exception("Failed to decline registration", exc_info=exc)
            await callback.answer("Не удалось отклонить регистрацию", show_alert=True)
            return

    admin_name = _admin_username(callback.from_user)
    base_caption = _build_profile_caption(snapshot)
    _remember_review_caption(callback.message, base_caption, overwrite=True)
    status_line = _format_result_line(False, [], admin_name)
    caption = _compose_caption(base_caption, status_line)

    if not await _edit_admin_message(
        callback.message,
        caption=caption,
        keyboard=None,
    ):
        await callback.answer("Не удалось обновить сообщение", show_alert=True)
        return

    await _send_user_notification(
        telegram_user_id,
        BLOCK_NOTIFICATION_TEXT,
        reply_markup=_build_user_button("Создать новый аккаунт", CREATE_ACCOUNT_LINK),
        parse_mode=None,
    )
    _forget_review_caption(callback.message)
    await callback.answer("Регистрация отклонена")


@dp.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    text = (
        "Привет! 👋 Добро пожаловать в приложение для знакомств Luvo — "
        "мы помогаем найти новые знакомства по твоим подпискам в Instagram. "
        "Чтобы начать знакомиться, запусти приложение! 💫"
    )
    await message.answer(text, reply_markup=feed_keyboard)


@dp.message(Command("rule"))
async def cmd_rule(message: types.Message) -> None:
    await message.answer(COMMUNITY_RULES_TEXT, parse_mode="HTML")


async def send_like_notification(chat_id: int) -> None:
    await bot.send_message(
        chat_id,
        "Кому-то понравился твой профиль ❤️ Узнай, кто это",
        reply_markup=likes_keyboard,
    )

async def send_match_notification(chat_id: int) -> None:
    await bot.send_message(
        chat_id,
        "Совпадение! 🔥 У вас взаимный интерес — начни общение",
        reply_markup=likes_keyboard,
    )


async def start_bot() -> None:
    await dp.start_polling(bot)
