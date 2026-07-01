import asyncio
import os
from html import escape

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.chat_action import ChatActionSender

from parser import search_and_get_download_link, download_mp3_to_temp

router = Router()

BANNER = os.path.join(os.path.dirname(__file__), "assets", "tg-banner.png")


class SearchStates(StatesGroup):
    waiting_for_track = State()


# ---------- тексты ----------

WELCOME = (
    "<b>🎵 Music Bot</b>\n"
    "Твой личный музыкальный поиск прямо в Telegram.\n\n"
    "Пришли мне <b>название трека</b> — найду его и отправлю готовым файлом. "
    "Быстро, бесплатно, без рекламы.\n\n"
    "Нажми <b>🔎 Найти музыку</b> или отправь /poisk."
)

HELP = (
    "<b>ℹ️ Как это работает</b>\n\n"
    "1️⃣ Нажми <b>🔎 Найти музыку</b> (или /poisk)\n"
    "2️⃣ Пришли <b>название трека</b> — можно с исполнителем\n"
    "3️⃣ Получи трек аудио-файлом 🎧\n\n"
    "<b>Команды</b>\n"
    "/start — главное меню\n"
    "/poisk — найти трек\n"
    "/help — эта справка"
)

ASK_TRACK = "🎧 Введи <b>название трека</b> (можно с исполнителем):"


# ---------- клавиатуры ----------

def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Найти музыку", callback_data="search")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="help")],
    ])


def again_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Найти ещё", callback_data="search")],
    ])


# ---------- команды ----------

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    if os.path.exists(BANNER):
        await message.answer_photo(FSInputFile(BANNER), caption=WELCOME, reply_markup=menu_kb())
    else:
        await message.answer(WELCOME, reply_markup=menu_kb())


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(HELP, reply_markup=menu_kb())


@router.message(Command("poisk"))
async def poisk_command(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_track)
    await message.answer(ASK_TRACK)


# ---------- инлайн-кнопки ----------

@router.callback_query(F.data == "search")
async def cb_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_track)
    await callback.message.answer(ASK_TRACK)
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.answer(HELP, reply_markup=menu_kb())
    await callback.answer()


# ---------- поиск трека ----------

@router.message(SearchStates.waiting_for_track)
async def process_track(message: Message, state: FSMContext):
    track_name = (message.text or "").strip()
    if not track_name:
        await message.answer("Пусто 🤔 Пришли название трека текстом.")
        return

    safe = escape(track_name)
    status = await message.answer(f"🔍 Ищу: <b>{safe}</b>…")

    # Блокирующий requests — уводим в поток, чтобы не морозить бота.
    link = await asyncio.to_thread(search_and_get_download_link, track_name)
    if not link:
        await status.edit_text("❌ Ничего не нашёл по этому запросу.\nПопробуй уточнить название 👇")
        await message.answer("Готов искать снова:", reply_markup=again_kb())
        await state.clear()
        return

    await status.edit_text(f"⬇️ Нашёл! Скачиваю: <b>{safe}</b>…")
    file_path = await asyncio.to_thread(download_mp3_to_temp, link, track_name)

    if file_path:
        try:
            async with ChatActionSender.upload_document(bot=message.bot, chat_id=message.chat.id):
                await message.answer_audio(
                    FSInputFile(file_path),
                    title=track_name,
                    caption="✅ Держи! Приятного прослушивания 🎶",
                    reply_markup=again_kb(),
                )
            await _cleanup(status, file_path)
            await state.clear()
            return
        except Exception as e:
            print(f"Не удалось отправить как аудио: {e}")
            try:
                await message.answer_document(
                    FSInputFile(file_path),
                    caption="✅ Готово (файлом) 🎶",
                    reply_markup=again_kb(),
                )
                await _cleanup(status, file_path)
                await state.clear()
                return
            except Exception as e2:
                print(f"Не удалось отправить как документ: {e2}")

    # Запасной вариант — кнопка со ссылкой
    await status.delete()
    await _send_link_button(message, safe, link)
    await state.clear()


# ---------- fallback на любое другое сообщение ----------

@router.message(StateFilter(None), F.text)
async def fallback(message: Message):
    await message.answer(
        "Чтобы найти трек — нажми кнопку ниже или отправь /poisk 👇",
        reply_markup=menu_kb(),
    )


# ---------- helpers ----------

async def _cleanup(status_message, file_path: str):
    try:
        os.remove(file_path)
    except OSError:
        pass
    try:
        await status_message.delete()
    except Exception:
        pass


async def _send_link_button(message: Message, safe_name: str, link: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬇️ Скачать трек", url=link)],
        [InlineKeyboardButton(text="🔎 Найти ещё", callback_data="search")],
    ])
    await message.answer(
        f"✅ Трек найден: <b>{safe_name}</b>\n"
        "Отправить файлом не вышло, но его можно скачать по кнопке ниже:",
        reply_markup=keyboard,
    )
