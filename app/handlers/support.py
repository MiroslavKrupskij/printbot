from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.db import fetchrow, execute
from app.enums import SupportStatus
from app.keyboards import support_request_kb

router = Router()

class SupportFSM(StatesGroup):
    topic = State()
    message = State()

async def _get_client_id_by_tg(tg_id: int):
    row = await fetchrow("SELECT client_id FROM clients WHERE telegram_id=$1", tg_id)
    return row["client_id"] if row else None

async def _admin_ids():
    row = await fetchrow("SELECT array_agg(telegram_id) AS ids FROM admins WHERE is_active=TRUE")
    return row["ids"] if row and row["ids"] else []

@router.callback_query(F.data == "SUPPORT:OPEN")
async def support_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SupportFSM.topic)
    await cb.message.edit_text(
        "Підтримка\n\n"
        "Вкажіть тему звернення одним коротким повідомленням («Питання по замовленню» і.т.д.)."
    )
    await cb.answer()

@router.message(SupportFSM.topic)
async def support_topic(message: Message, state: FSMContext):
    topic = (message.text or "").strip()
    if len(topic) < 3:
        await message.answer("Тема занадто коротка. Введіть, будь ласка, тему ще раз.")
        return

    await state.update_data(topic=topic)
    await state.set_state(SupportFSM.message)
    await message.answer("Опишіть детально проблему одним повідомленням.")

@router.message(SupportFSM.message)
async def support_message(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    client_id = await _get_client_id_by_tg(tg_id)
    if not client_id:
        await message.answer("Клієнта не знайдено. Натисніть /start і повторіть спробу.")
        await state.clear()
        return

    data = await state.get_data()
    topic = data["topic"]
    text = (message.text or "").strip()

    if len(text) < 5:
        await message.answer("Опишіть детальніше (мінімум 5 символів).")
        return

    row = await fetchrow(
        """
        INSERT INTO support_requests (client_id, topic, message, status)
        VALUES ($1, $2, $3, $4)
        RETURNING request_id
        """,
        client_id, topic, text, SupportStatus.OPEN.value
    )
    request_id = row["request_id"]

    await state.clear()
    await message.answer(
        f"✅ Звернення №{request_id} прийнято.\n"
        f"Чекайте на відповідь менеджера."
    )

    for admin_tg in await _admin_ids():
        try:
            await message.bot.send_message(
                admin_tg,
                "🆘 Нове звернення підтримки\n"
                f"Request ID: {request_id}\n"
                f"Client TG: {tg_id}\n"
                f"Тема: {topic}\n\n"
                f"{text}",
                reply_markup=support_request_kb(request_id)
            )
        except Exception:
            pass