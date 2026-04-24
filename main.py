import asyncio
from aiogram import Bot, Dispatcher
from os import getenv

from router import router
from dotenv import load_dotenv


load_dotenv()

TOKEN = getenv("BOT_TOKEN")
async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print('Starting...')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())