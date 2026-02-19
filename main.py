import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.config import settings
from app.db import init_db_pool, close_db_pool
from app.handlers.start import router as start_router

async def main():
    logging.basicConfig(level=logging.INFO)

    await init_db_pool()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(start_router)

    try:
        await dp.start_polling(bot)
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())
