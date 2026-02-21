from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.db import fetchrow, execute
from app.texts import status_ua
from app.enums import OrderStatus, ActorRole
from app.keyboards import price_confirm_kb

router = Router()

class AdminFSM(StatesGroup):
    set_price = State()
    set_price_comment = State()
    support_reply = State()

async def _is_admin(tg_id: int) -> bool:
    row = await fetchrow(
        "SELECT admin_id FROM admins WHERE telegram_id=$1 AND is_active=TRUE",
        tg_id,
    )
    return row is not None

async def _log_status(
    order_id: int,
    old_status: str | None,
    new_status: str,
    tg_id: int,
    comment: str | None,
):
    await execute(
        """
        INSERT INTO order_status_history
            (order_id, old_status, new_status, changed_by_role, changed_by_telegram_id, comment)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        order_id,
        old_status,
        new_status,
        ActorRole.ADMIN.value,
        tg_id,
        comment,
    )

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Нові замовлення", callback_data="ADMIN:LIST:NEW")],
            [InlineKeyboardButton(text="💳 Оплачені замовлення", callback_data="ADMIN:LIST:PAYMENT_REPORTED")],
            [InlineKeyboardButton(text="🛠 Замовлення, які виконуються", callback_data="ADMIN:LIST:IN_PROGRESS")],
            [InlineKeyboardButton(text="✅ Готові замовлення", callback_data="ADMIN:LIST:READY")],
            [InlineKeyboardButton(text="🆘 Заявки в підтримку", callback_data="ADMIN:SUPPORT:LIST")],
        ]
    )

def orders_list_kb(order_ids: list[int], back_to_menu: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Замовлення №{oid}", callback_data=f"ADMIN:OPEN:{oid}")]
        for oid in order_ids
    ]
    if back_to_menu:
        rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="ADMIN:MENU")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_kb(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=target)]])

def order_actions_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if status == OrderStatus.NEW.value:
        rows.append([InlineKeyboardButton(text="💰 Встановити ціну", callback_data=f"ADMIN:SET_PRICE:{order_id}")])

    if status in {OrderStatus.PAYMENT_REPORTED.value, OrderStatus.IN_PROGRESS.value}:
        rows.append([InlineKeyboardButton(text="📎 Показати файли", callback_data=f"ADMIN:FILES:{order_id}")])

    if status == OrderStatus.PAYMENT_REPORTED.value:
        rows.append([InlineKeyboardButton(text="✅ Оплату підтверджено", callback_data=f"ADMIN:STATUS:{order_id}:IN_PROGRESS")])
        rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ADMIN:STATUS:{order_id}:CANCELED")])

    if status == OrderStatus.IN_PROGRESS.value:
        rows.append([InlineKeyboardButton(text="✅ Готово", callback_data=f"ADMIN:STATUS:{order_id}:READY")])
        rows.append([InlineKeyboardButton(text="🏁 Завершити", callback_data=f"ADMIN:STATUS:{order_id}:DONE")])
        rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ADMIN:STATUS:{order_id}:CANCELED")])

    if status == OrderStatus.READY.value:
        rows.append([InlineKeyboardButton(text="🏁 Завершити", callback_data=f"ADMIN:STATUS:{order_id}:DONE")])
        rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ADMIN:STATUS:{order_id}:CANCELED")])

    rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="ADMIN:MENU")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def support_list_kb(request_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Звернення №{rid}", callback_data=f"ADMIN:SUPPORT:OPEN:{rid}")]
        for rid in request_ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="ADMIN:MENU")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def support_actions_kb(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Відповісти", callback_data=f"ADMIN:SUPPORT:REPLY:{request_id}")],
            [InlineKeyboardButton(text="✅ Закрити", callback_data=f"ADMIN:SUPPORT:CLOSE:{request_id}")],
            [InlineKeyboardButton(text="⬅️ До списку", callback_data="ADMIN:SUPPORT:LIST")],
        ]
    )

async def _get_order(order_id: int):
    return await fetchrow(
        """
        SELECT o.order_id, o.client_id, o.category, o.service, o.quantity, o.comment_client,
               o.status, o.price_amount, o.price_comment,
               c.telegram_id AS client_tg
        FROM orders o
        JOIN clients c ON c.client_id=o.client_id
        WHERE o.order_id=$1
        """,
        order_id,
    )

def _order_text(order: dict) -> str:
    order_id = order["order_id"]
    price = order["price_amount"]
    price_str = f"{price:.2f} грн" if price is not None else "-"

    status_code = order["status"]
    status_str = f"{status_ua(status_code)} ({status_code})"

    return (
        f"Замовлення №{order_id}\n"
        f"Статус: {status_str}\n"
        f"{order['category']} → {order['service']}\n"
        f"Кількість: {order['quantity']}\n"
        f"Коментар клієнта: {order['comment_client'] or '-'}\n"
        f"Ціна: {price_str}\n"
        f"Коментар до ціни: {order['price_comment'] or '-'}\n"
    )

_STATUS_TO_TIMEFIELD = {
    OrderStatus.IN_PROGRESS.value: "in_progress_at",
    OrderStatus.READY.value: "ready_at",
    OrderStatus.DONE.value: "done_at",
    OrderStatus.CANCELED.value: "canceled_at",
}

async def _send_order_files(target: Message, order_id: int):
    row = await fetchrow(
        """
        SELECT json_agg(t ORDER BY t.created_at ASC) AS items
        FROM (
            SELECT role, tg_file_id, file_name, mime_type, created_at
            FROM order_files
            WHERE order_id=$1
            ORDER BY created_at ASC
        ) t
        """,
        order_id,
    )

    items = row["items"] if row and row["items"] else []
    if not items:
        await target.answer(f"Файлів для замовлення №{order_id} немає.")
        return

    await target.answer(f"📎 Файли для замовлення №{order_id}:")

    for it in items:
        role = it.get("role")
        tg_file_id = it.get("tg_file_id")
        mime = (it.get("mime_type") or "").lower()
        name = it.get("file_name") or "file"
        caption = f"{role} • {name}"

        try:
            if mime.startswith("image/"):
                await target.bot.send_photo(chat_id=target.chat.id, photo=tg_file_id, caption=caption)
            else:
                await target.bot.send_document(chat_id=target.chat.id, document=tg_file_id, caption=caption)
        except Exception:
            try:
                await target.bot.send_document(chat_id=target.chat.id, document=tg_file_id, caption=caption)
            except Exception:
                pass

async def _close_support_with_reply(bot, request_id: int, reply_text: str) -> str:
    row = await fetchrow(
        """
        SELECT sr.request_id, sr.status, sr.topic,
               c.telegram_id AS client_tg
        FROM support_requests sr
        JOIN clients c ON c.client_id = sr.client_id
        WHERE sr.request_id=$1
        """,
        request_id,
    )
    if not row:
        return f"Звернення №{request_id} не знайдено."

    if row["status"] != "OPEN":
        return f"Звернення №{request_id} вже закрите."

    client_tg = int(row["client_tg"])

    await bot.send_message(
        client_tg,
        "📩 Відповідь підтримки\n"
        f"Звернення №{request_id}\n"
        f"Тема: {row['topic']}\n\n"
        f"{reply_text}",
    )

    await execute(
        "UPDATE support_requests SET status='CLOSED', closed_at=now() WHERE request_id=$1",
        request_id,
    )
    return f"✅ Відповідь на звернення №{request_id} надіслано. Звернення закрито."

async def _close_support_without_reply(request_id: int) -> str:
    row = await fetchrow(
        "SELECT request_id, status FROM support_requests WHERE request_id=$1",
        request_id,
    )
    if not row:
        return "Звернення не знайдено."
    if row["status"] != "OPEN":
        return "Воно вже закрите."

    await execute(
        "UPDATE support_requests SET status='CLOSED', closed_at=now() WHERE request_id=$1",
        request_id,
    )
    return f"✅ Звернення №{request_id} закрито."

@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not await _is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        return
    await message.answer("Адмін-меню:", reply_markup=admin_menu_kb())

@router.callback_query(F.data == "ADMIN:MENU")
async def admin_menu(cb: CallbackQuery, state: FSMContext):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return
    await state.clear()
    await cb.message.edit_text("Адмін-меню:", reply_markup=admin_menu_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:LIST:"))
async def admin_list(cb: CallbackQuery):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    status = cb.data.split(":")[-1]
    row = await fetchrow(
        """
        SELECT array_agg(order_id ORDER BY created_at DESC) AS ids
        FROM orders
        WHERE status=$1
        """,
        status,
    )
    ids = row["ids"] if row and row["ids"] else []
    if not ids:
        await cb.message.edit_text(f"Замовлень зі статусом {status_ua(status)} ({status}) немає ✅", reply_markup=admin_menu_kb())
        await cb.answer()
        return

    await cb.message.edit_text(f"Оберіть замовлення ({status_ua(status)}):", reply_markup=orders_list_kb(ids))
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:OPEN:"))
async def admin_open_order(cb: CallbackQuery):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    order_id = int(cb.data.split(":")[-1])
    order = await _get_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    await cb.message.edit_text(_order_text(order), reply_markup=order_actions_kb(order_id, order["status"]))
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:SET_PRICE:"))
async def admin_set_price_start(cb: CallbackQuery, state: FSMContext):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    order_id = int(cb.data.split(":")[-1])
    order = await _get_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] != OrderStatus.NEW.value:
        await cb.answer("Ціну можна ставити лише для нових замовлень.", show_alert=True)
        return

    await state.clear()
    await state.update_data(order_id=order_id)
    await state.set_state(AdminFSM.set_price)

    await cb.message.edit_text(
        f"Замовлення №{order_id}\n"
        f"{order['category']} → {order['service']}\n"
        f"Кількість: {order['quantity']}\n\n"
        "Введіть ціну у гривнях:",
        reply_markup=back_kb(f"ADMIN:OPEN:{order_id}"),
    )
    await cb.answer()

@router.message(AdminFSM.set_price)
async def admin_set_price_value(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = float(raw)
    except ValueError:
        await message.answer("Некоректна ціна. Спробуйте ще раз.")
        return

    if price < 0:
        await message.answer("Ціна не може бути від’ємною.")
        return

    await state.update_data(price_amount=price)
    await state.set_state(AdminFSM.set_price_comment)
    await message.answer("Додайте коментар до ціни або надішліть «-», якщо без коментаря.")

@router.message(AdminFSM.set_price_comment)
async def admin_set_price_comment(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data["order_id"])
    price_amount = float(data["price_amount"])

    price_comment = (message.text or "").strip()
    if price_comment == "-":
        price_comment = None

    order = await _get_order(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        await state.clear()
        return

    if order["status"] != OrderStatus.NEW.value:
        await message.answer("Ціну можна встановити лише для замовлення зі статусом NEW.")
        await state.clear()
        return

    old_status = order["status"]
    new_status = OrderStatus.PRICE_SENT.value

    await execute(
        """
        UPDATE orders
        SET price_amount=$2,
            price_comment=$3,
            price_sent_at=now(),
            status=$4
        WHERE order_id=$1
        """,
        order_id,
        price_amount,
        price_comment,
        new_status,
    )

    await _log_status(
        order_id=order_id,
        old_status=old_status,
        new_status=new_status,
        tg_id=message.from_user.id,
        comment=f"price_amount={price_amount}; price_comment={(price_comment or '-')}",
    )

    client_tg = int(order["client_tg"])
    text_to_client = (
        "💰 Розрахунок вартості замовлення готовий!\n"
        f"Замовлення №{order_id}\n"
        f"{order['category']} → {order['service']}\n"
        f"Кількість: {order['quantity']}\n"
        f"Ціна: {price_amount:.2f} грн\n"
        f"Коментар: {(price_comment or '-')}\n\n"
        "Підтвердіть замовлення щоб ми почали роботу."
    )
    await message.bot.send_message(client_tg, text_to_client, reply_markup=price_confirm_kb(order_id))

    await state.clear()
    await message.answer(f"✅ Ціну відправлено клієнту для замовлення №{order_id}.")

@router.callback_query(F.data.startswith("ADMIN:STATUS:"))
async def admin_set_status(cb: CallbackQuery):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    parts = cb.data.split(":")
    order_id = int(parts[2])
    new_status = parts[3]

    order = await _get_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    old_status = order["status"]

    if new_status not in (
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.READY.value,
        OrderStatus.DONE.value,
        OrderStatus.CANCELED.value,
    ):
        await cb.answer("Невідомий статус.", show_alert=True)
        return

    allowed = {
        OrderStatus.PAYMENT_REPORTED.value: {OrderStatus.IN_PROGRESS.value, OrderStatus.CANCELED.value},
        OrderStatus.IN_PROGRESS.value: {OrderStatus.READY.value, OrderStatus.DONE.value, OrderStatus.CANCELED.value},
        OrderStatus.READY.value: {OrderStatus.DONE.value, OrderStatus.CANCELED.value},
    }
    if old_status in allowed and new_status not in allowed[old_status]:
        await cb.answer(f"Не можна: {old_status} → {new_status}", show_alert=True)
        return
    if old_status not in allowed:
        await cb.answer(f"Цей статус не підтримує зміну тут: {old_status}", show_alert=True)
        return

    time_field = _STATUS_TO_TIMEFIELD.get(new_status)
    cancel_reason = None
    comment = None

    if new_status == OrderStatus.CANCELED.value:
        cancel_reason = "Скасовано адміністратором"
        comment = cancel_reason

    if new_status == OrderStatus.CANCELED.value:
        await execute(
            f"""
            UPDATE orders
            SET status=$2,
                {time_field}=now(),
                cancel_reason=$3
            WHERE order_id=$1
            """,
            order_id,
            new_status,
            cancel_reason,
        )
    else:
        await execute(
            f"""
            UPDATE orders
            SET status=$2,
                {time_field}=now()
            WHERE order_id=$1
            """,
            order_id,
            new_status,
        )

    await _log_status(order_id, old_status, new_status, cb.from_user.id, comment)

    client_tg = int(order["client_tg"])
    try:
        await cb.bot.send_message(
            client_tg,
            f"ℹ️ Статус замовлення №{order_id} оновлено: {status_ua(new_status)}",
        )
    except Exception:
        pass

    await cb.answer("Оновлено ✅", show_alert=True)

    refreshed = await _get_order(order_id)
    await cb.message.edit_text(_order_text(refreshed), reply_markup=order_actions_kb(order_id, refreshed["status"]))

@router.callback_query(F.data.startswith("ADMIN:FILES:"))
async def admin_files_cb(cb: CallbackQuery):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    order_id = int(cb.data.split(":")[-1])
    await _send_order_files(cb.message, order_id)
    await cb.answer()

@router.message(Command("order_files"))
async def admin_files_cmd(message: Message, command: CommandObject):
    if not await _is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        return

    args = (command.args or "").strip()
    if not args or not args.isdigit():
        await message.answer("Формат: /order_files <order_id>")
        return

    order_id = int(args)
    await _send_order_files(message, order_id)

@router.callback_query(F.data == "ADMIN:SUPPORT:LIST")
async def admin_support_list(cb: CallbackQuery):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    row = await fetchrow(
        """
        SELECT array_agg(request_id ORDER BY created_at DESC) AS ids
        FROM support_requests
        WHERE status='OPEN'
        """
    )
    ids = row["ids"] if row and row["ids"] else []
    if not ids:
        await cb.message.edit_text("Відкритих звернень немає ✅", reply_markup=admin_menu_kb())
        await cb.answer()
        return

    await cb.message.edit_text("Відкриті звернення підтримки:", reply_markup=support_list_kb(ids))
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:SUPPORT:OPEN:"))
async def admin_support_open(cb: CallbackQuery):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    request_id = int(cb.data.split(":")[-1])
    row = await fetchrow(
        """
        SELECT sr.request_id, sr.status, sr.topic, sr.message, sr.created_at,
               c.telegram_id AS client_tg
        FROM support_requests sr
        JOIN clients c ON c.client_id = sr.client_id
        WHERE sr.request_id=$1
        """,
        request_id,
    )
    if not row:
        await cb.answer("Звернення не знайдено.", show_alert=True)
        return

    text = (
        "🆘 Звернення підтримки\n"
        f"Request ID: {row['request_id']}\n"
        f"Статус: {row['status']}\n"
        f"Client TG: {row['client_tg']}\n"
        f"Тема: {row['topic']}\n\n"
        f"{row['message']}"
    )
    await cb.message.edit_text(text, reply_markup=support_actions_kb(request_id))
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:SUPPORT:REPLY:"))
async def admin_support_reply_start(cb: CallbackQuery, state: FSMContext):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    request_id = int(cb.data.split(":")[-1])

    row = await fetchrow("SELECT request_id, status FROM support_requests WHERE request_id=$1", request_id)
    if not row:
        await cb.answer("Звернення не знайдено.", show_alert=True)
        return
    if row["status"] != "OPEN":
        await cb.answer("Звернення вже закрите.", show_alert=True)
        return

    await state.clear()
    await state.update_data(support_request_id=request_id)
    await state.set_state(AdminFSM.support_reply)

    await cb.message.edit_text(
        f"✍️ Відповідь на звернення №{request_id}\n\n"
        "Надішліть текст відповіді одним повідомленням:",
        reply_markup=back_kb(f"ADMIN:SUPPORT:OPEN:{request_id}"),
    )
    await cb.answer()

@router.message(AdminFSM.support_reply)
async def admin_support_reply_send(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    data = await state.get_data()
    request_id = int(data["support_request_id"])

    reply_text = (message.text or "").strip()
    if len(reply_text) < 2:
        await message.answer("Текст відповіді занадто короткий.")
        return

    result = await _close_support_with_reply(message.bot, request_id, reply_text)

    await state.clear()
    await message.answer(result)

@router.callback_query(F.data.startswith("ADMIN:SUPPORT:CLOSE:"))
async def admin_support_close(cb: CallbackQuery, state: FSMContext):
    if not await _is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    request_id = int(cb.data.split(":")[-1])
    await state.clear()

    result = await _close_support_without_reply(request_id)
    await cb.answer("Готово ✅", show_alert=True)
    await cb.message.edit_text(result, reply_markup=back_kb("ADMIN:SUPPORT:LIST"))

@router.message(Command("support_reply"))
async def support_reply_cmd(message: Message, command: CommandObject):
    if not await _is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        return

    args = (command.args or "").strip()
    if not args:
        await message.answer("Формат: /support_reply <request_id> <текст відповіді>")
        return

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /support_reply <request_id> <текст відповіді>")
        return

    try:
        request_id = int(parts[0])
    except ValueError:
        await message.answer("request_id має бути числом. Приклад: /support_reply 2 Дякуємо, зараз перевіримо.")
        return

    reply_text = parts[1].strip()
    if len(reply_text) < 2:
        await message.answer("Текст відповіді занадто короткий.")
        return

    result = await _close_support_with_reply(message.bot, request_id, reply_text)
    await message.answer(result)