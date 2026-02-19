from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from app.db import fetchrow, execute
from app.keyboards import phone_request_kb

router = Router()

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
            "Вітаю! Для користування ботом надішліть номер телефону.",
            reply_markup=phone_request_kb()
        )
        return

    await message.answer(
        "З поверненням! Телефон уже збережено, можемо переходити до каталогу послуг.",
        reply_markup=ReplyKeyboardRemove()
    )


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
        reply_markup=ReplyKeyboardRemove()
    )
