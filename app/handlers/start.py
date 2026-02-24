from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from app.keyboards import (
    phone_request_kb, persistent_menu_kb,
    main_menu_kb, back_to_menu_kb,
)
from app.handlers.admin import admin_menu_kb
from app.services.auth import is_admin
from app.services.clients import get_client_by_tg_id, upsert_client_from_contact
from app.texts import (
    contacts_text_md, help_text_md, location_text_md,
    ARTEL_LAT, ARTEL_LON,
)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    client = await get_client_by_tg_id(tg_id)

    if client is None or not client["phone"]:
        await message.answer(
            "Вітаю! Для користування ботом поділіться номером телефону.",
            reply_markup=phone_request_kb()
        )
        return

    if await is_admin(tg_id):
        await message.answer("🔸 Адмін-меню:", reply_markup=persistent_menu_kb())
        await message.answer("🔸 Адмін-меню:", reply_markup=admin_menu_kb())
    else:
        await message.answer("З поверненням! 👋", reply_markup=persistent_menu_kb())
        await message.answer("🔸 Меню користувача:", reply_markup=main_menu_kb())

@router.message(F.contact)
async def got_contact(message: Message):
    if not message.contact or message.contact.user_id != message.from_user.id:
        await message.answer("Будь ласка, надішліть свій номер телефону кнопкою нижче.")
        return

    tg_id = message.from_user.id
    username = message.from_user.username
    full_name = (message.from_user.full_name or "").strip()
    phone = message.contact.phone_number

    await upsert_client_from_contact(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
        phone=phone,
    )

    await message.answer("Дякую! Номер збережено ✅", reply_markup=persistent_menu_kb())
    await message.answer("🔸 Меню користувача:", reply_markup=main_menu_kb())

@router.message(F.text == "☰ Меню")
async def open_menu(message: Message):
    tg_id = message.from_user.id

    if await is_admin(tg_id):
        await message.answer("🔸 Адмін-меню:", reply_markup=admin_menu_kb())
        return

    client = await get_client_by_tg_id(tg_id)
    if client is None or not client["phone"]:
        await message.answer(
            "Для користування ботом поділіться номером телефону.",
            reply_markup=phone_request_kb()
        )
        return

    await message.answer("🔸 Меню користувача:", reply_markup=main_menu_kb())

@router.callback_query(F.data == "CLIENT:MENU")
async def client_menu_cb(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🔸 Меню користувача:", reply_markup=main_menu_kb())

@router.callback_query(F.data == "CONTACTS:OPEN")
async def contacts_open(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        contacts_text_md(),
        reply_markup=back_to_menu_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "LOCATION:OPEN")
async def location_open(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        location_text_md(),
        reply_markup=back_to_menu_kb(),
        parse_mode="Markdown"
    )
    await cb.message.answer_location(latitude=ARTEL_LAT, longitude=ARTEL_LON)

@router.callback_query(F.data == "HELP:OPEN")
async def help_open(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        help_text_md(),
        reply_markup=back_to_menu_kb(),
        parse_mode="Markdown"
    )