import logging
from aiogram.types import InlineKeyboardMarkup
from app.services.auth import admin_ids

logger = logging.getLogger(__name__)

async def notify_admins(bot, text: str, reply_markup: InlineKeyboardMarkup | None = None, parse_mode: str | None = None):
    for admin_tg in await admin_ids():
        try:
            await bot.send_message(admin_tg, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            logger.exception("notify_admins failed admin_tg=%s", admin_tg)

async def notify_admins_copy_message(bot, from_chat_id: int, message_id: int):
    for admin_tg in await admin_ids():
        try:
            await bot.copy_message(chat_id=admin_tg, from_chat_id=from_chat_id, message_id=message_id)
        except Exception:
            logger.exception("notify_admins_copy_message failed admin_tg=%s", admin_tg)