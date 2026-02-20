from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.db import fetchrow, execute
from app.enums import OrderStatus, ActorRole

router = Router()


class OrderFSM(StatesGroup):
    qty = State()
    comment = State()


def qty_cancel_kb(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"CAT:{category}")],
    ])


async def _get_client_id_by_tg(tg_id: int):
    row = await fetchrow("SELECT client_id FROM clients WHERE telegram_id=$1", tg_id)
    return row["client_id"] if row else None


@router.callback_query(F.data.startswith("ORDER:START:"))
async def order_start(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    if len(parts) < 4:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    category = parts[2]
    service = ":".join(parts[3:])

    await state.clear()
    await state.update_data(category=category, service=service)

    await state.set_state(OrderFSM.qty)
    await cb.message.edit_text(
        f"Оформлення замовлення\n"
        f"Послуга: {category} → {service}\n\n"
        f"Вкажіть кількість (ціле число, наприклад 100 або 1000):",
        reply_markup=qty_cancel_kb(category)
    )
    await cb.answer()


@router.message(OrderFSM.qty)
async def qty_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    # Дозволяємо лише цифри без пробілів/ком
    if not text.isdigit():
        await message.answer("Будь ласка, введіть кількість як ціле число (наприклад 1000).")
        return

    qty = int(text)

    # Мінімальні обмеження — можна підлаштувати
    if qty <= 0:
        await message.answer("Кількість має бути більшою за 0. Введіть число ще раз.")
        return

    if qty > 100000:
        await message.answer("Занадто велике число. Введіть кількість до 100000.")
        return

    await state.update_data(qty=qty)
    await state.set_state(OrderFSM.comment)

    data = await state.get_data()
    category = data.get("category")
    service = data.get("service")

    await message.answer(
        f"Послуга: {category} → {service}\n"
        f"Кількість: {qty}\n\n"
        f"Ви можете залишити коментар менеджеру, або \"-\", якщо без коментаря."
    )


@router.message(OrderFSM.comment)
async def save_order(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    client_id = await _get_client_id_by_tg(tg_id)
    if not client_id:
        await message.answer("Клієнта не знайдено. Натисніть /start і повторіть спробу.")
        await state.clear()
        return

    data = await state.get_data()
    category = data["category"]
    service = data["service"]
    qty = int(data.get("qty", 1))

    comment_client = (message.text or "").strip()
    if comment_client == "-":
        comment_client = None

    row = await fetchrow(
        """
        INSERT INTO orders
            (client_id, category, service, quantity, comment_client, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING order_id
        """,
        client_id, category, service, qty, comment_client, OrderStatus.NEW.value
    )
    order_id = row["order_id"]

    await execute(
        """
        INSERT INTO order_status_history
            (order_id, old_status, new_status, changed_by_role,
             changed_by_telegram_id, comment)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        order_id,
        OrderStatus.NEW.value,
        OrderStatus.NEW.value,
        ActorRole.CLIENT.value,
        tg_id,
        "created"
    )

    await state.clear()

    await message.answer(
        f"✅ Замовлення успішно створено!\n"
        f"ID: {order_id}\n"
        f"{category} → {service}\n"
        f"Кількість: {qty}\n"
        f"Статус: {OrderStatus.NEW.value}\n\n"
        f"Очікуйте, менеджер розрахує ціну та надішле повідомлення для підтвердження."
    )