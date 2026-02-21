from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from app.db import fetchrow, execute
from app.keyboards import phone_request_kb, persistent_menu_kb
from app.handlers.admin import admin_menu_kb, _is_admin

router = Router()

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Каталог послуг", callback_data="CATALOG:OPEN")],
        [InlineKeyboardButton(text="🆘 Підтримка", callback_data="SUPPORT:OPEN")],
    ])

async def _get_client_by_tg_id(tg_id: int):
    return await fetchrow(
        "SELECT client_id, telegram_id, phone FROM clients WHERE telegram_id=$1",
        tg_id
    )

@router.message(CommandStart())
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    client = await _get_client_by_tg_id(tg_id)

    if client is None or not client["phone"]:
        await message.answer(
            "Вітаю! Для користування ботом поділіться номером телефону.",
            reply_markup=phone_request_kb()
        )
        return

    if await _is_admin(tg_id):
        await message.answer(
            "Адмін-меню:",
            reply_markup=persistent_menu_kb()
        )
        await message.answer("Оберіть дію:", reply_markup=admin_menu_kb())
    else:
        await message.answer(
            "З поверненням! 👋",
            reply_markup=persistent_menu_kb()
        )
        await message.answer("Меню:", reply_markup=main_menu_kb())

@router.message(F.contact)
async def got_contact(message: Message):
    if not message.contact or message.contact.user_id != message.from_user.id:
        await message.answer("Будь-ласка, надішліть свій номер телефону.")
        return

    tg_id = message.from_user.id
    username = message.from_user.username
    full_name = (message.from_user.full_name or "").strip()
    phone = message.contact.phone_number

    client = await _get_client_by_tg_id(tg_id)

    if client is None:
        await execute(
            """
            INSERT INTO clients(telegram_id, username, full_name, phone)
            VALUES ($1, $2, $3, $4)
            """,
            tg_id, username, full_name, phone
        )
    else:
        await execute(
            """
            UPDATE clients
            SET username=$2, full_name=$3, phone=$4
            WHERE telegram_id=$1
            """,
            tg_id, username, full_name, phone
        )

    await message.answer(
        "Дякую! Номер збережено ✅",
        reply_markup=persistent_menu_kb()
    )
    await message.answer("Меню:", reply_markup=main_menu_kb())

@router.message(F.text == "☰ Меню")
async def open_menu(message: Message):
    tg_id = message.from_user.id

    if await _is_admin(tg_id):
        await message.answer("Адмін-меню:", reply_markup=admin_menu_kb())
        return

    client = await _get_client_by_tg_id(tg_id)

    if client is None or not client["phone"]:
        await message.answer(
            "Для користування ботом поділіться номером телефону.",
            reply_markup=phone_request_kb()
        )
        return

    await message.answer("Меню:", reply_markup=main_menu_kb())