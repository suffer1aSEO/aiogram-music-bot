import asyncio
import logging
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv

from router import router

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

COMMANDS = [
    BotCommand(command="start", description="🎵 Главное меню"),
    BotCommand(command="poisk", description="🔎 Найти музыку"),
    BotCommand(command="help", description="ℹ️ Как это работает"),
]


async def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN не задан. Создай .env (см. .env.example).")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logging.info("Starting @%s …", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
