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

class NeedInfoFSM(StatesGroup):
    msg = State()

def qty_cancel_kb(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"CAT:{category}")],
    ])

def my_orders_kb(order_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Замовлення №{oid}", callback_data=f"ORDERS:OPEN:{oid}")]
        for oid in order_ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="CLIENT:MENU")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def order_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ До списку", callback_data="ORDERS:MY")],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data="CLIENT:MENU")],
    ])

def admin_need_info_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Відповісти", callback_data=f"ADMIN:NEED_REPLY:{order_id}")],
        [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=f"ADMIN:OPEN:{order_id}")],
    ])

def admin_payment_reported_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплату підтверджено", callback_data=f"ADMIN:STATUS:{order_id}:IN_PROGRESS")],
        [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=f"ADMIN:OPEN:{order_id}")],
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

async def _log_status(
    order_id: int,
    old_status: str | None,
    new_status: str,
    role: str,
    tg_id: int,
    comment: str | None
):
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
        f"Послуга: {category} ➡️ {service}\n\n"
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
        f"Послуга: {category} ➡️ {service}\n"
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
        f"{category} ➡️ {service}\n"
        f"Кількість: {qty}\n"
        f"Статус: {status_ua(OrderStatus.NEW.value)}\n\n"
        "Очікуйте, менеджер розрахує ціну та надішле повідомлення для підтвердження."
    )

    for admin_tg in await _admin_ids():
        try:
            await message.bot.send_message(
                admin_tg,
                "📦 Нове замовлення!\n"
                f"№{order_id}\n"
                f"{category} ➡️ {service}\n"
                f"Кількість: {qty}\n"
                f"Коментар: {comment_client or '-'}\n"
                f"Статус: {OrderStatus.NEW.value}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=f"ADMIN:OPEN:{order_id}")]
                ])
            )
        except Exception:
            pass

@router.callback_query(F.data == "ORDERS:MY")
async def orders_my(cb: CallbackQuery):
    client_id = await _get_client_id_by_tg(cb.from_user.id)
    if not client_id:
        await cb.answer("Натисніть /start і поділіться номером телефону.", show_alert=True)
        return

    row = await fetchrow(
        """
        SELECT array_agg(order_id ORDER BY created_at DESC) AS ids
        FROM orders
        WHERE client_id=$1
        """,
        client_id
    )
    ids = row["ids"] if row and row["ids"] else []
    if not ids:
        await cb.message.edit_text(
            "У вас ще немає замовлень.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Меню", callback_data="CLIENT:MENU")]
            ])
        )
        await cb.answer()
        return

    ids = [int(x) for x in ids][:10]
    await cb.message.edit_text("Ваші замовлення:", reply_markup=my_orders_kb(ids))
    await cb.answer()

@router.callback_query(F.data.startswith("ORDERS:OPEN:"))
async def orders_open(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[-1])

    client_id = await _get_client_id_by_tg(cb.from_user.id)
    if not client_id:
        await cb.answer("Натисніть /start і поділіться номером телефону.", show_alert=True)
        return

    order = await fetchrow(
        """
        SELECT order_id, category, service, quantity, comment_client, status, price_amount, price_comment
        FROM orders
        WHERE order_id=$1 AND client_id=$2
        """,
        order_id, client_id
    )
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    status = order["status"]
    price = order["price_amount"]
    price_str = f"{price:.2f} грн" if price is not None else "-"

    text = (
        f"Замовлення №{order_id}\n"
        f"Статус: {status_ua(status)} ({status})\n"
        f"{order['category']} ➡️ {order['service']}\n"
        f"Кількість: {order['quantity']}\n"
        f"Коментар клієнта: {order['comment_client'] or '-'}\n"
        f"Ціна: {price_str}\n"
        f"Коментар до ціни: {order['price_comment'] or '-'}"
    )

    if status == OrderStatus.PRICE_SENT.value:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтверджую", callback_data=f"ORDER:CONFIRM:{order_id}")],
            [InlineKeyboardButton(text="❓ Потрібне уточнення", callback_data=f"ORDER:NEED_INFO:{order_id}")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ORDER:CANCEL:{order_id}")],
            [InlineKeyboardButton(text="⬅️ До списку", callback_data="ORDERS:MY")],
            [InlineKeyboardButton(text="⬅️ Меню", callback_data="CLIENT:MENU")],
        ])
    elif status == OrderStatus.CONFIRMED.value:
        kb = payment_actions_kb(order_id)
    elif status == OrderStatus.NEED_INFO.value:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Продовжити", callback_data=f"ORDER:CONTINUE:{order_id}")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ORDER:CANCEL:{order_id}")],
            [InlineKeyboardButton(text="⬅️ До списку", callback_data="ORDERS:MY")],
            [InlineKeyboardButton(text="⬅️ Меню", callback_data="CLIENT:MENU")],
        ])
    else:
        kb = order_back_kb()

    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

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
async def order_need_info(cb: CallbackQuery, state: FSMContext):
    order_id = int(cb.data.split(":")[-1])
    order = await _get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    old_status = order["status"]
    new_status = OrderStatus.NEED_INFO.value

    await execute("UPDATE orders SET status=$2 WHERE order_id=$1", order_id, new_status)
    await _log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client needs info")

    await state.clear()
    await state.update_data(need_info_order_id=order_id)
    await state.set_state(NeedInfoFSM.msg)

    await cb.message.edit_text(
        f"✅ Прийнято. Для замовлення №{order_id} потрібні уточнення.\n\n"
        "✍️ Будь-ласка, напишіть що саме потрібно уточнити (одним повідомленням)."
    )
    await cb.answer()

@router.message(NeedInfoFSM.msg)
async def need_info_message(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = int(data.get("need_info_order_id") or 0)
    if not order_id:
        await message.answer("Не вдалося визначити замовлення. Натисніть «☰ Меню» і повторіть.")
        await state.clear()
        return

    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст уточнення занадто короткий. Спробуйте ще раз.")
        return

    await _log_status(
        order_id=order_id,
        old_status=None,
        new_status=OrderStatus.NEED_INFO.value,
        role=ActorRole.CLIENT.value,
        tg_id=message.from_user.id,
        comment=f"Уточнення клієнта: {text}"
    )

    for admin_tg in await _admin_ids():
        try:
            await message.bot.send_message(
                admin_tg,
                "❓ Уточнення від клієнта\n"
                f"Замовлення №{order_id}\n"
                f"Client TG: {message.from_user.id}\n\n"
                f"{text}",
                reply_markup=admin_need_info_kb(order_id)
            )
        except Exception:
            pass

    await state.clear()
    await message.answer("✅ Дякуємо! Ми передали уточнення менеджеру. Очікуйте на відповідь.")

@router.callback_query(F.data.startswith("ORDER:CONTINUE:"))
async def order_continue(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[-1])

    order = await _get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] != OrderStatus.NEED_INFO.value:
        await cb.answer("Замовлення вже можна продовжувати зі свого статусу.", show_alert=True)
        await orders_open(cb)
        return

    old_status = order["status"]
    next_status = OrderStatus.PRICE_SENT.value if order["price_amount"] is not None else OrderStatus.NEW.value

    await execute("UPDATE orders SET status=$2 WHERE order_id=$1", order_id, next_status)
    await _log_status(
        order_id=order_id,
        old_status=old_status,
        new_status=next_status,
        role=ActorRole.CLIENT.value,
        tg_id=cb.from_user.id,
        comment="client продолжив після NEED_INFO"
    )

    await orders_open(cb)
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

    await cb.message.edit_text(
        f"❌ Замовлення №{order_id} скасовано.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Меню", callback_data="CLIENT:MENU")]
        ])
    )

    for admin_tg in await _admin_ids():
        try:
            await cb.bot.send_message(
                admin_tg,
                f"❌ Клієнт скасував замовлення №{order_id} (було {status_ua(str(old_status))})."
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

    if order["status"] not in (
        OrderStatus.CONFIRMED.value,
        OrderStatus.PAYMENT_REPORTED.value,
        OrderStatus.IN_PROGRESS.value
    ):
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
        f"✅ Квитанцію з оплатою замовлення №{order_id} отримано.\n"
        "Адміністратор перевірить оплату та оновить статус замовлення. Очікуйте на повідомлення."
    )

    for admin_tg in await _admin_ids():
        try:
            price = order["price_amount"]
            price_str = f"{price:.2f} грн" if price is not None else "-"

            await message.bot.send_message(
                admin_tg,
                "📎 Квитанція з оплатою отримана\n"
                f"Замовлення №{order_id}\n"
                f"{order['category']} ➡️ {order['service']}\n"
                f"Кількість: {order['quantity']}\n"
                f"Ціна: {price_str}\n"
                f"Статус: {OrderStatus.PAYMENT_REPORTED.value}",
                reply_markup=admin_payment_reported_kb(order_id)
            )

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