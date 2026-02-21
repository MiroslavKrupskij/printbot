from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.db import fetchrow, execute
from app.texts import status_ua
from app.enums import OrderStatus, ActorRole, FileRole
from app.keyboards import payment_actions_kb

router = Router()

class OrderFSM(StatesGroup):
    qty = State()
    comment = State()

class PaymentFSM(StatesGroup):
    proof = State()

def qty_cancel_kb(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"CAT:{category}")],
    ])

async def _get_client_id_by_tg(tg_id: int):
    row = await fetchrow("SELECT client_id FROM clients WHERE telegram_id=$1", tg_id)
    return row["client_id"] if row else None

async def _get_order_with_client(order_id: int):
    return await fetchrow(
        """
        SELECT o.order_id, o.client_id, o.status, o.price_amount, o.category, o.service, o.quantity,
               c.telegram_id AS client_tg
        FROM orders o
        JOIN clients c ON c.client_id = o.client_id
        WHERE o.order_id = $1
        """,
        order_id
    )

async def _admin_ids():
    row = await fetchrow("SELECT array_agg(telegram_id) AS ids FROM admins WHERE is_active=TRUE")
    return row["ids"] if row and row["ids"] else []

async def _log_status(order_id: int, old_status: str | None, new_status: str, role: str, tg_id: int, comment: str | None):
    await execute(
        """
        INSERT INTO order_status_history
            (order_id, old_status, new_status, changed_by_role, changed_by_telegram_id, comment)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        order_id, old_status, new_status, role, tg_id, comment
    )

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
        "Оформлення замовлення\n"
        f"Послуга: {category} → {service}\n\n"
        "Вкажіть кількість:",
        reply_markup=qty_cancel_kb(category)
    )
    await cb.answer()

@router.message(OrderFSM.qty)
async def qty_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Введіть кількість як ціле число (наприклад 1000).")
        return

    qty = int(text)
    if qty <= 0:
        await message.answer("Кількість має бути більшою за 0.")
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
        "Залиште коментар менеджеру або надішліть «-», якщо без коментаря."
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
        INSERT INTO orders (client_id, category, service, quantity, comment_client, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING order_id
        """,
        client_id, category, service, qty, comment_client, OrderStatus.NEW.value
    )
    order_id = row["order_id"]

    await _log_status(
        order_id=order_id,
        old_status=OrderStatus.NEW.value,
        new_status=OrderStatus.NEW.value,
        role=ActorRole.CLIENT.value,
        tg_id=tg_id,
        comment="created"
    )

    await state.clear()

    await message.answer(
        "✅ Замовлення успішно створено!\n"
        f"ID: {order_id}\n"
        f"{category} → {service}\n"
        f"Кількість: {qty}\n"
        f"Статус: {status_ua(OrderStatus.NEW.value)}\n\n"
        "Очікуйте, менеджер розрахує ціну та надішле повідомлення для підтвердження."
    )

@router.callback_query(F.data.startswith("ORDER:CONFIRM:"))
async def order_confirm(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[-1])
    order = await _get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] != OrderStatus.PRICE_SENT.value:
        await cb.answer("Це замовлення зараз не очікує підтвердження ціни.", show_alert=True)
        return

    old_status = order["status"]
    new_status = OrderStatus.CONFIRMED.value

    await execute(
        "UPDATE orders SET status=$2, confirmed_at=now() WHERE order_id=$1",
        order_id, new_status
    )
    await _log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client confirmed price")

    price_amount = order["price_amount"]
    price_str = f"{price_amount:.2f} грн" if price_amount is not None else "-"

    await cb.message.edit_text(
        "✅ Дякую! Замовлення підтверджено.\n"
        f"Замовлення №{order_id}\n"
        f"Ціна: {price_str}\n\n"
        "Після оплати натисніть «Я оплатив(-ла)» і завантажте квитанцію.",
        reply_markup=payment_actions_kb(order_id)
    )

    for admin_tg in await _admin_ids():
        try:
            await cb.bot.send_message(admin_tg, f"✅ Клієнт підтвердив ціну по замовленню №{order_id}.")
        except Exception:
            pass

    await cb.answer()

@router.callback_query(F.data.startswith("ORDER:NEED_INFO:"))
async def order_need_info(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[-1])
    order = await _get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    old_status = order["status"]
    new_status = OrderStatus.NEED_INFO.value

    await execute("UPDATE orders SET status=$2 WHERE order_id=$1", order_id, new_status)
    await _log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client needs info")

    await cb.message.edit_text(
        f"✅ Прийнято. Для замовлення №{order_id} потрібні уточнення.\n"
        "✍️ Опишіть що саме потрібно уточнити одним повідомленням у чат."
    )

    for admin_tg in await _admin_ids():
        try:
            await cb.bot.send_message(admin_tg, f"❓ Клієнт просить уточнення по замовленню №{order_id}.")
        except Exception:
            pass

    await cb.answer()

@router.callback_query(F.data.startswith("ORDER:CANCEL:"))
async def order_cancel(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[-1])
    order = await _get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] == OrderStatus.CANCELED.value:
        await cb.answer("Вже скасовано.", show_alert=True)
        return

    old_status = order["status"]
    new_status = OrderStatus.CANCELED.value

    await execute(
        "UPDATE orders SET status=$2, canceled_at=now(), cancel_reason=$3 WHERE order_id=$1",
        order_id, new_status, "Скасовано клієнтом"
    )
    await _log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client canceled")

    await cb.message.edit_text(f"❌ Замовлення №{order_id} скасовано.")

    for admin_tg in await _admin_ids():
        try:
            old_code = old_status.value if hasattr(old_status, "value") else str(old_status)
            await cb.bot.send_message(
                admin_tg,
                f"❌ Клієнт скасував замовлення №{order_id} (було {status_ua(old_code)})."
            )
        except Exception:
            pass

    await cb.answer()

@router.callback_query(F.data.startswith("PAY:REPORTED:"))
async def pay_reported(cb: CallbackQuery, state: FSMContext):
    order_id = int(cb.data.split(":")[-1])
    order = await _get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] not in (OrderStatus.CONFIRMED.value, OrderStatus.PAYMENT_REPORTED.value, OrderStatus.IN_PROGRESS.value):
        await cb.answer("Цей крок доступний після підтвердження ціни.", show_alert=True)
        return

    await state.clear()
    await state.update_data(order_id=order_id)
    await state.set_state(PaymentFSM.proof)

    await cb.message.edit_text(
        f"📎 Завантажте фото або PDF-документ квитанції з оплати замовлення №{order_id}."
    )
    await cb.answer()

@router.message(PaymentFSM.proof, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def payment_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = int(data["order_id"])

    order = await _get_order_with_client(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        await state.clear()
        return

    tg_file_id = None
    file_name = None
    mime_type = None

    if message.photo:
        tg_file_id = message.photo[-1].file_id
        file_name = "photo.jpg"
        mime_type = "image/jpeg"
    elif message.document:
        tg_file_id = message.document.file_id
        file_name = message.document.file_name
        mime_type = message.document.mime_type

    if not tg_file_id:
        await message.answer("Не вдалося отримати файл. Спробуйте ще раз.")
        return

    await execute(
        """
        INSERT INTO order_files(order_id, role, tg_file_id, file_name, mime_type)
        VALUES ($1, $2, $3, $4, $5)
        """,
        order_id, FileRole.PAYMENT_PROOF.value, tg_file_id, file_name, mime_type
    )

    if order["status"] != OrderStatus.PAYMENT_REPORTED.value:
        old_status = order["status"]
        new_status = OrderStatus.PAYMENT_REPORTED.value

        await execute(
            "UPDATE orders SET status=$2, payment_reported_at=now() WHERE order_id=$1",
            order_id, new_status
        )
        await _log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, message.from_user.id, "payment proof uploaded")

    await state.clear()

    await message.answer(
        f"✅ Квитанцію з оплати замовлення №{order_id} отримано.\n"
        "Адміністратор перевірить оплату та оновить статус. Очікуйте на повідомлення."
    )

    for admin_tg in await _admin_ids():
        try:
            await message.bot.send_message(admin_tg, f"📎 Квитанція з оплатою замовленню №{order_id}:")
            await message.bot.copy_message(
                chat_id=admin_tg,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception:
            pass

@router.message(PaymentFSM.proof)
async def payment_wrong_content(message: Message):
    await message.answer("Будь-ласка, надішліть фото або документ з квитанцією.")