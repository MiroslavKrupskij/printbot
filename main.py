import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db import init_db_pool, close_db_pool
from app.handlers.start import router as start_router
from app.handlers.catalog import router as catalog_router
from app.handlers.order_flow import router as order_flow_router
from app.handlers.support import router as support_router
from app.handlers.admin import router as admin_router

async def main():
    logging.basicConfig(level=logging.INFO)

    await init_db_pool()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(order_flow_router)
    dp.include_router(support_router)
    dp.include_router(admin_router)

    try:
        await dp.start_polling(bot)
    finally:
        await close_db_pool()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass