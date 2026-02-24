from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.keyboards import support_request_kb
from app.services.auth import get_client_id_by_tg
from app.services.support_service import create_support_request, notify_admins_about_support
from app.texts import support_topic_prompt, support_message_prompt

router = Router()

class SupportFSM(StatesGroup):
    topic = State()
    message = State()

@router.callback_query(F.data == "SUPPORT:OPEN")
async def support_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SupportFSM.topic)
    await cb.message.edit_text(support_topic_prompt())
    await cb.answer()

@router.message(SupportFSM.topic)
async def support_topic(message: Message, state: FSMContext):
    topic = (message.text or "").strip()
    if len(topic) < 3:
        await message.answer("Тема занадто коротка. Введіть, будь ласка, тему ще раз.")
        return

    await state.update_data(topic=topic)
    await state.set_state(SupportFSM.message)
    await message.answer(support_message_prompt())

@router.message(SupportFSM.message)
async def support_message(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    client_id = await get_client_id_by_tg(tg_id)
    if not client_id:
        await message.answer("Клієнта не знайдено. Натисніть /start і повторіть спробу.")
        await state.clear()
        return

    data = await state.get_data()
    topic = (data.get("topic") or "").strip()
    text = (message.text or "").strip()

    if len(text) < 5:
        await message.answer("Опишіть детальніше (мінімум 5 символів).")
        return

    request_id = await create_support_request(client_id, topic, text)

    await state.clear()
    await message.answer(
        f"✅ Звернення №{request_id} прийнято.\n"
        "Чекайте на відповідь менеджера."
    )

    await notify_admins_about_support(
        bot=message.bot,
        request_id=request_id,
        client_tg=tg_id,
        topic=topic,
        text=text,
        reply_markup=support_request_kb(request_id),
    )