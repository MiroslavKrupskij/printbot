import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db import init_db_pool, close_db_pool
from app.handlers.start import router as start_router
from app.handlers.catalog import router as catalog_router
from app.handlers.order_flow import router as order_flow_router

async def main():
    logging.basicConfig(level=logging.INFO)

    await init_db_pool()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(order_flow_router)

    try:
        await dp.start_polling(bot)
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())
