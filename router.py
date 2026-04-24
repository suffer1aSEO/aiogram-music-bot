from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import os

from parser import search_and_get_download_link, download_mp3_to_temp

router = Router()


# Состояния для FSM
class SearchStates(StatesGroup):
    waiting_for_track = State()


# Обработчик команды /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Приветствую! Я бот для скачивания музыки бесплатно!\n"
        "Воспользуйся командой /poisk чтобы найти музыку"
    )


# Обработчик команды /poisk
@router.message(Command("poisk"))
async def poisk_command(message: types.Message, state: FSMContext):
    await message.answer("Введи название трека который хочешь найти!")
    await state.set_state(SearchStates.waiting_for_track)


# Обработчик текстового сообщения (названия трека)
@router.message(SearchStates.waiting_for_track)
async def process_track(message: types.Message, state: FSMContext):
    track_name = message.text.strip()

    # Сообщаем пользователю, что ищем
    await message.answer(f"🔍 Ищу трек: *{track_name}*...", parse_mode="Markdown")

    # Получаем ссылку на MP3
    download_link = search_and_get_download_link(track_name)

    if download_link:
        # =============================================
        # СПОСОБ 1: Скачиваем и отправляем как аудио
        # =============================================
        file_path = download_mp3_to_temp(download_link, track_name)

        if file_path:
            try:
                # Отправляем аудиофайл
                audio_file = FSInputFile(file_path)
                await message.answer_audio(
                    audio=audio_file,
                    title=track_name,
                    caption="✅ Вот что удалось найти по вашему запросу"
                )

                # Удаляем временный файл
                os.remove(file_path)
                print(f"Временный файл удалён: {file_path}")

            except Exception as e:
                print(f"Ошибка при отправке аудио: {e}")

                # Если не получилось отправить как аудио — отправляем как документ
                try:
                    doc_file = FSInputFile(file_path)
                    await message.answer_document(
                        document=doc_file,
                        caption="✅ Вот что удалось найти по вашему запросу (в виде файла)"
                    )
                    os.remove(file_path)
                except Exception as e2:
                    print(f"Ошибка при отправке файла: {e2}")
                    # Запасной вариант — кнопка со ссылкой
                    await send_fallback_button(message, track_name, download_link)
            else:
                # Всё отправилось успешно — выходим
                await state.clear()
                return

        # =============================================
        # СПОСОБ 2: Если скачать не удалось — кнопка
        # =============================================
        await send_fallback_button(message, track_name, download_link)

    else:
        await message.answer(
            "❌ Ничего не найдено, попробуйте ввести другую песню\n/poisk - для повторного поиска трека!"
        )

    # Сбрасываем состояние
    await state.clear()


async def send_fallback_button(message: types.Message, track_name: str, download_link: str):
    """
    Запасной вариант: отправляет сообщение с кнопкой для скачивания
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬇️ Скачать трек", url=download_link)]
    ])


    await message.answer(
        f"✅ Ваш трек найден!\n\n"
        f"🎵 *{track_name}*\n"
        f"Не удалось отправить файл напрямую, но вы можете скачать его по кнопке ниже:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )