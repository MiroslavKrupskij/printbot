from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.texts import (
    status_ua, format_price, render_order_card,
    render_price_sent_to_client, render_admin_client_info, render_admin_support_request
)
from app.enums import OrderStatus, ActorRole
from app.keyboards import (
    admin_menu_kb, orders_list_kb, admin_back_kb,
    order_actions_kb, support_list_kb,
    support_actions_kb, price_confirm_kb,
    admin_after_message_kb, admin_client_info_kb,
)
from app.services.auth import is_admin
from app.services.clients import get_client_by_id
from app.services.orders import (
    get_admin_order, log_status, list_order_ids_by_status,
    set_price_and_mark_price_sent,
)
from app.services.admin_files import send_order_files_to_admin_chat
from app.services.admin_messaging import send_manager_message_to_client, close_need_info
from app.services.admin_status import admin_change_order_status
from app.services.support_service import (
    close_support_with_reply,
    close_support_without_reply,
    list_open_support_request_ids,
    get_support_request_with_client,
    get_support_request,
)
from app.utils.callbacks import (
    CallbackParseError,
    parse_admin_list, parse_admin_open,
    parse_admin_client, parse_admin_client_msg,
    parse_admin_need_close, parse_admin_need_reply,
    parse_admin_set_price, parse_admin_status,
    parse_admin_files, parse_admin_support_action,
    cb_admin_menu, cb_admin_client, cb_admin_support_open,
)

router = Router()

class AdminFSM(StatesGroup):
    set_price = State()
    set_price_comment = State()
    support_reply = State()
    need_info_reply = State()
    client_message = State()

@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        return

    await message.answer("🔸 Адмін-меню:", reply_markup=admin_menu_kb())

@router.callback_query(F.data == "ADMIN:MENU")
async def admin_menu(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    await state.clear()
    await cb.message.edit_text("🔸 Адмін-меню:", reply_markup=admin_menu_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:LIST:"))
async def admin_list(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        status = parse_admin_list(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    ids = await list_order_ids_by_status(status)
    if not ids:
        await cb.message.edit_text(
            f"Замовлень зі статусом {status_ua(status)} ({status}) немає ✅",
            reply_markup=admin_menu_kb()
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        f"Оберіть замовлення ({status_ua(status)}):",
        reply_markup=orders_list_kb(ids)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:OPEN:"))
async def admin_open_order(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id = parse_admin_open(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    order = await get_admin_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    await cb.message.edit_text(
        render_order_card(order),
        reply_markup=order_actions_kb(order_id, order["status"])
    )
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:CLIENT:"))
async def admin_client_info(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    await state.clear()

    try:
        order_id = parse_admin_client(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    order = await get_admin_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    client = await get_client_by_id(int(order["client_id"]))
    if not client:
        await cb.answer("Клієнта не знайдено.", show_alert=True)
        return

    text = render_admin_client_info(client)
    kb = admin_client_info_kb(order_id)

    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:CLIENT_MSG:"))
async def admin_client_message_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id = parse_admin_client_msg(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    order = await get_admin_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    await state.clear()
    await state.update_data(client_msg_order_id=order_id)
    await state.set_state(AdminFSM.client_message)

    await cb.message.edit_text(
        f"✉️ Повідомлення клієнту • замовлення №{order_id}\n\n"
        "Надішліть текст одним повідомленням:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_admin_client(order_id))],
            [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_admin_menu())],
        ])
    )
    await cb.answer()

@router.message(AdminFSM.client_message)
async def admin_client_message_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data.get("client_msg_order_id") or 0)
    if not order_id:
        await message.answer("Помилка стану. Поверніться в адмін-меню і спробуйте ще раз.")
        await state.clear()
        return

    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст занадто короткий. Спробуйте ще раз.")
        return

    ok, msg = await send_manager_message_to_client(
        bot=message.bot,
        order_id=order_id,
        admin_tg_id=message.from_user.id,
        text=text,
    )

    if not ok:
        await message.answer(msg)
        await state.clear()
        return

    await state.clear()

    await message.answer(
        msg,
        reply_markup=admin_after_message_kb(order_id)
    )

@router.callback_query(F.data.startswith("ADMIN:NEED_CLOSE:"))
async def admin_need_close(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id = parse_admin_need_close(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    ok, alert, _ = await close_need_info(
        bot=cb.bot,
        order_id=order_id,
        admin_tg_id=cb.from_user.id,
        reply_text=None,
    )

    if not ok:
        await cb.answer(alert, show_alert=True)
        return

    await cb.answer(alert, show_alert=True)

    refreshed = await get_admin_order(order_id)
    await cb.message.edit_text(
        render_order_card(refreshed),
        reply_markup=order_actions_kb(order_id, refreshed["status"]),
    )

@router.callback_query(F.data.startswith("ADMIN:NEED_REPLY:"))
async def admin_need_reply_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id = parse_admin_need_reply(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    order = await get_admin_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    await state.clear()
    await state.update_data(need_info_order_id=order_id)
    await state.set_state(AdminFSM.need_info_reply)

    await cb.message.edit_text(
        f"💬 Відповідь клієнту по замовленню №{order_id}\n\n"
        "Надішліть текст відповіді одним повідомленням:",
        reply_markup=admin_back_kb(f"ADMIN:OPEN:{order_id}"),
    )
    await cb.answer()

@router.message(AdminFSM.need_info_reply)
async def admin_need_reply_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data["need_info_order_id"])

    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст відповіді занадто короткий.")
        return

    ok, alert, _ = await close_need_info(
        bot=message.bot,
        order_id=order_id,
        admin_tg_id=message.from_user.id,
        reply_text=text,
    )

    if not ok:
        await message.answer(alert)
        await state.clear()
        return

    await state.clear()
    await message.answer(f"✅ {alert}")

@router.callback_query(F.data.startswith("ADMIN:SET_PRICE:"))
async def admin_set_price_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id = parse_admin_set_price(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    order = await get_admin_order(order_id)
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
        f"{order['category']} ➡️ {order['service']}\n"
        f"Кількість: {order['quantity']}\n\n"
        "Введіть ціну у гривнях:",
        reply_markup=admin_back_kb(f"ADMIN:OPEN:{order_id}"),
    )
    await cb.answer()

@router.message(AdminFSM.set_price)
async def admin_set_price_value(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = Decimal(raw)
    except (InvalidOperation, ValueError):
        await message.answer("Некоректна ціна. Введіть число, наприклад: 120 або 120.50")
        return

    if price < 0:
        await message.answer("Ціна не може бути від’ємною.")
        return

    price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    await state.update_data(price_amount=price)
    await state.set_state(AdminFSM.set_price_comment)
    await message.answer("Додайте коментар до ціни або надішліть «-», якщо без коментаря.")

@router.message(AdminFSM.set_price_comment)
async def admin_set_price_comment(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data["order_id"])

    price_amount = data.get("price_amount")
    if price_amount is None:
        await message.answer("Помилка стану: ціна не знайдена. Почніть встановлення ціни заново.")
        await state.clear()
        return

    price_comment = (message.text or "").strip()
    if price_comment == "-":
        price_comment = None

    order = await get_admin_order(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        await state.clear()
        return

    if order["status"] != OrderStatus.NEW.value:
        await message.answer("Ціну можна встановити лише для замовлення зі статусом NEW.")
        await state.clear()
        return

    old_status = order["status"]
    new_status = await set_price_and_mark_price_sent(order_id, price_amount, price_comment)

    await log_status(
        order_id=order_id,
        old_status=old_status,
        new_status=new_status,
        role=ActorRole.ADMIN.value,
        tg_id=message.from_user.id,
        comment=f"price_amount={format_price(price_amount)}; price_comment={(price_comment or '-')}",
    )

    client_tg = int(order["client_tg"])
    text_to_client = render_price_sent_to_client(order_id, order, price_amount, price_comment)
    await message.bot.send_message(client_tg, text_to_client, reply_markup=price_confirm_kb(order_id))

    await state.clear()
    await message.answer(f"✅ Ціну відправлено клієнту для замовлення №{order_id}.")

@router.callback_query(F.data.startswith("ADMIN:STATUS:"))
async def admin_set_status(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id, new_status = parse_admin_status(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    order = await get_admin_order(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    old_status = order["status"]

    result = await admin_change_order_status(
        order_id=order_id,
        old_status=old_status,
        new_status=new_status,
        admin_tg_id=cb.from_user.id,
    )

    if not result.ok:
        await cb.answer(result.alert, show_alert=True)
        return

    client_tg = int(order["client_tg"])
    if result.client_msg:
        try:
            await cb.bot.send_message(client_tg, result.client_msg)
        except Exception:
            pass

    await cb.answer(result.alert, show_alert=True)

    refreshed = await get_admin_order(order_id)
    await cb.message.edit_text(
        render_order_card(refreshed),
        reply_markup=order_actions_kb(order_id, refreshed["status"]),
    )

@router.callback_query(F.data.startswith("ADMIN:FILES:"))
async def admin_files_cb(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        order_id, role_filter = parse_admin_files(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    chat_id = cb.message.chat.id if cb.message else cb.from_user.id

    async def reply_text(t: str):
        await cb.bot.send_message(chat_id, t)

    await send_order_files_to_admin_chat(
        bot=cb.bot,
        chat_id=chat_id,
        order_id=order_id,
        role_filter=role_filter,
        reply=reply_text,
    )
    await cb.answer()

@router.message(Command("order_files"))
async def admin_files_cmd(message: Message, command: CommandObject):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        return

    args = (command.args or "").strip()
    if not args or not args.isdigit():
        await message.answer("Формат: /order_files <order_id>")
        return

    order_id = int(args)
    await send_order_files_to_admin_chat(
        bot=message.bot,
        chat_id=message.chat.id,
        order_id=order_id,
        role_filter=None,
        reply=message.answer,
    )

@router.callback_query(F.data == "ADMIN:SUPPORT:LIST")
async def admin_support_list(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    ids = await list_open_support_request_ids(limit=50)
    if not ids:
        await cb.message.edit_text("Відкритих звернень немає ✅", reply_markup=admin_menu_kb())
        await cb.answer()
        return

    await cb.message.edit_text("Відкриті звернення підтримки:", reply_markup=support_list_kb(ids))
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:SUPPORT:OPEN:"))
async def admin_support_open(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        action, request_id = parse_admin_support_action(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    if action != "OPEN":
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    row = await get_support_request_with_client(request_id)
    if not row:
        await cb.answer("Звернення не знайдено.", show_alert=True)
        return

    text = render_admin_support_request(row)
    await cb.message.edit_text(text, reply_markup=support_actions_kb(request_id))
    await cb.answer()

@router.callback_query(F.data.startswith("ADMIN:SUPPORT:REPLY:"))
async def admin_support_reply_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        action, request_id = parse_admin_support_action(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    if action != "REPLY":
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    row = await get_support_request(request_id)
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
        reply_markup=admin_back_kb(cb_admin_support_open(request_id)),
    )
    await cb.answer()

@router.message(AdminFSM.support_reply)
async def admin_support_reply_send(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Доступ заборонено.")
        await state.clear()
        return

    data = await state.get_data()
    request_id = int(data["support_request_id"])

    reply_text = (message.text or "").strip()
    if len(reply_text) < 2:
        await message.answer("Текст відповіді занадто короткий.")
        return

    result = await close_support_with_reply(message.bot, request_id, reply_text)

    await state.clear()
    await message.answer(result)

@router.callback_query(F.data.startswith("ADMIN:SUPPORT:CLOSE:"))
async def admin_support_close(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        await cb.answer("Доступ заборонено.", show_alert=True)
        return

    try:
        action, request_id = parse_admin_support_action(cb.data)
    except CallbackParseError:
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    if action != "CLOSE":
        await cb.answer("Некоректна кнопка.", show_alert=True)
        return

    await state.clear()

    result = await close_support_without_reply(request_id)
    await cb.answer("Готово ✅", show_alert=True)
    await cb.message.edit_text(result, reply_markup=admin_back_kb("ADMIN:SUPPORT:LIST"))

@router.message(Command("support_reply"))
async def support_reply_cmd(message: Message, command: CommandObject):
    if not await is_admin(message.from_user.id):
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

    result = await close_support_with_reply(message.bot, request_id, reply_text)
    await message.answer(result)