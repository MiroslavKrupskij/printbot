from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.enums import OrderStatus, ActorRole, FileRole
from app.texts import (
    render_order_card, render_admin_new_order,
    render_admin_payment_received, render_payment_instructions,
    render_admin_need_info, render_admin_cancel,
)
from app.keyboards import (
    qty_cancel_kb, my_orders_kb, order_back_kb,
    add_design_kb, after_payment_prompt_kb, confirmed_actions_kb,
    admin_need_info_kb, admin_payment_reported_kb,
    client_created_order_kb, client_empty_orders_kb,
    order_price_sent_kb, order_need_info_actions_kb,
    cancel_reason_back_kb, after_cancel_kb,
    client_menu_only_kb, client_open_order_and_menu_kb,
    admin_open_order_kb, admin_design_files_kb
)
from app.services.auth import get_client_id_by_tg
from app.services.catalog_service import get_category_name, get_service_name
from app.services.orders import (
    get_order_with_client, log_status,
    create_order, list_client_order_ids, get_client_order,
    update_status_simple, update_status_confirmed,
    update_status_canceled, update_status_payment_reported,
)
from app.services.files import add_order_file
from app.services.notify import notify_admins, notify_admins_copy_message
from app.utils.callbacks import (
    CallbackParseError,
    parse_order_start, parse_orders_open,
    parse_order_confirm, parse_order_need_info, parse_order_continue, parse_order_cancel,
    parse_design_add, parse_pay_reported,
)

router = Router()

class OrderFSM(StatesGroup):
    qty = State()
    comment = State()

class PaymentFSM(StatesGroup):
    proof = State()

class NeedInfoFSM(StatesGroup):
    msg = State()

class DesignFSM(StatesGroup):
    file = State()

class CancelFSM(StatesGroup):
    reason = State()

@router.callback_query(F.data.startswith("ORDER:START:"))
async def order_start(cb: CallbackQuery, state: FSMContext):
    try:
        cat_id, svc_id = parse_order_start(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    category = get_category_name(cat_id)
    service = get_service_name(cat_id, svc_id)

    if category is None or service is None:
        await cb.answer("Невірні дані послуги.", show_alert=True)
        return

    await state.clear()
    await state.update_data(category=category, service=service)

    await state.set_state(OrderFSM.qty)
    await cb.message.edit_text(
        "Оформлення замовлення\n"
        f"Послуга: {category} ➡️ {service}\n\n"
        "Вкажіть кількість:",
        reply_markup=qty_cancel_kb(cat_id)
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
    client_id = await get_client_id_by_tg(tg_id)
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

    order_id = await create_order(
        client_id=client_id,
        category=category,
        service=service,
        quantity=qty,
        comment_client=comment_client,
    )

    await log_status(
        order_id=order_id,
        old_status=OrderStatus.NEW.value,
        new_status=OrderStatus.NEW.value,
        role=ActorRole.CLIENT.value,
        tg_id=tg_id,
        comment="created"
    )

    await state.clear()

    await message.answer(
        f"✅ Замовлення №{order_id} створено.\n"
        "Менеджер надішле вам ціну після розрахунку.",
        reply_markup=client_created_order_kb()
    )

    await notify_admins(
        message.bot,
        render_admin_new_order(order_id, category, service, qty, comment_client),
        reply_markup=admin_open_order_kb(order_id),
    )

@router.callback_query(F.data == "ORDERS:MY")
async def orders_my(cb: CallbackQuery):
    client_id = await get_client_id_by_tg(cb.from_user.id)
    if not client_id:
        await cb.answer("Натисніть /start і поділіться номером телефону.", show_alert=True)
        return

    ids = await list_client_order_ids(client_id, limit=10)
    if not ids:
        await cb.message.edit_text(
            "У вас ще немає замовлень.",
            reply_markup=client_empty_orders_kb()
        )
        await cb.answer()
        return

    ids = [int(x) for x in ids][:10]
    await cb.message.edit_text("Ваші замовлення:", reply_markup=my_orders_kb(ids))
    await cb.answer()

@router.callback_query(F.data.startswith("ORDERS:OPEN:"))
async def orders_open(cb: CallbackQuery):
    try:
        order_id = parse_orders_open(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    client_id = await get_client_id_by_tg(cb.from_user.id)
    if not client_id:
        await cb.answer("Натисніть /start і поділіться номером телефону.", show_alert=True)
        return

    order = await get_client_order(order_id, client_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    status = order["status"]
    text = render_order_card(order)

    if status == OrderStatus.PRICE_SENT.value:
        kb = order_price_sent_kb(order_id)
    elif status == OrderStatus.CONFIRMED.value:
        kb = confirmed_actions_kb(order_id)
    elif status == OrderStatus.NEED_INFO.value:
        kb = order_need_info_actions_kb(order_id)
    elif status in {OrderStatus.PAYMENT_REPORTED.value, OrderStatus.IN_PROGRESS.value, OrderStatus.READY.value}:
        kb = add_design_kb(order_id)
    else:
        kb = order_back_kb()

    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("ORDER:CONFIRM:"))
async def order_confirm(cb: CallbackQuery):
    try:
        order_id = parse_order_confirm(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    order = await get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] != OrderStatus.PRICE_SENT.value:
        await cb.answer("Це замовлення зараз не очікує підтвердження ціни.", show_alert=True)
        return

    old_status = order["status"]
    new_status = OrderStatus.CONFIRMED.value

    await update_status_confirmed(order_id, new_status)
    await log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client confirmed price")

    await cb.message.edit_text(
        render_payment_instructions(order_id, order.get("price_amount")),
        reply_markup=confirmed_actions_kb(order_id),
        parse_mode="HTML",
    )

    await notify_admins(
        cb.bot,
        f"✅ Клієнт підтвердив ціну по замовленню №{order_id}.",
        reply_markup=admin_open_order_kb(order_id),
    )

    await cb.answer()

@router.callback_query(F.data.startswith("ORDER:NEED_INFO:"))
async def order_need_info(cb: CallbackQuery, state: FSMContext):
    try:
        order_id = parse_order_need_info(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    order = await get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    old_status = order["status"]
    new_status = OrderStatus.NEED_INFO.value

    await update_status_simple(order_id, new_status)
    await log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client needs info")

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

    await log_status(
        order_id=order_id,
        old_status=None,
        new_status=OrderStatus.NEED_INFO.value,
        role=ActorRole.CLIENT.value,
        tg_id=message.from_user.id,
        comment=f"Уточнення клієнта: {text}"
    )

    await notify_admins(
        message.bot,
        render_admin_need_info(order_id, message.from_user.id, text),
        reply_markup=admin_need_info_kb(order_id),
    )

    await state.clear()
    await message.answer("✅ Дякуємо! Ми передали уточнення менеджеру. Очікуйте на відповідь.")


@router.callback_query(F.data.startswith("ORDER:CONTINUE:"))
async def order_continue(cb: CallbackQuery):
    try:
        order_id = parse_order_continue(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    order = await get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] != OrderStatus.NEED_INFO.value:
        await cb.answer("Замовлення вже можна продовжувати зі свого статусу.", show_alert=True)
        await orders_open(cb)
        return

    old_status = order["status"]
    next_status = OrderStatus.PRICE_SENT.value if order["price_amount"] is not None else OrderStatus.NEW.value

    await update_status_simple(order_id, next_status)
    await log_status(
        order_id=order_id,
        old_status=old_status,
        new_status=next_status,
        role=ActorRole.CLIENT.value,
        tg_id=cb.from_user.id,
        comment="client continued after NEED_INFO"
    )

    await orders_open(cb)
    await cb.answer()

@router.callback_query(F.data.startswith("ORDER:CANCEL:"))
async def order_cancel(cb: CallbackQuery, state: FSMContext):
    try:
        order_id = parse_order_cancel(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    order = await get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] == OrderStatus.CANCELED.value:
        await cb.answer("Вже скасовано.", show_alert=True)
        return

    need_reason_statuses = {
        OrderStatus.PAYMENT_REPORTED.value,
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.READY.value,
        OrderStatus.DONE.value,
    }
    if order["status"] in need_reason_statuses:
        await state.clear()
        await state.update_data(cancel_order_id=order_id)
        await state.set_state(CancelFSM.reason)

        await cb.message.edit_text(
            f"❌ Скасування замовлення №{order_id}\n\n"
            "Це замовлення вже після оплати/в роботі.\n"
            "Будь ласка, напишіть причину скасування одним повідомленням:",
            reply_markup=cancel_reason_back_kb(order_id)
        )
        await cb.answer()
        return

    old_status = order["status"]
    new_status = OrderStatus.CANCELED.value

    await update_status_canceled(order_id, new_status, "Скасовано клієнтом")
    await log_status(order_id, old_status, new_status, ActorRole.CLIENT.value, cb.from_user.id, "client canceled")

    await cb.message.edit_text(
        f"❌ Замовлення №{order_id} скасовано.",
        reply_markup=client_menu_only_kb()
    )

    await notify_admins(
        cb.bot,
        render_admin_cancel(order_id, old_status, "Скасовано клієнтом"),
        reply_markup=admin_open_order_kb(order_id),
    )

    await cb.answer()

@router.message(CancelFSM.reason)
async def cancel_reason_message(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = int(data.get("cancel_order_id") or 0)
    if not order_id:
        await message.answer("Помилка. Спробуйте ще раз через список замовлень.")
        await state.clear()
        return

    reason = (message.text or "").strip()
    if len(reason) < 3:
        await message.answer("Причина занадто коротка. Напишіть, будь ласка, детальніше.")
        return

    order = await get_order_with_client(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        await state.clear()
        return

    if order["status"] == OrderStatus.CANCELED.value:
        await message.answer("Це замовлення вже скасовано.")
        await state.clear()
        return

    old_status = order["status"]
    new_status = OrderStatus.CANCELED.value

    await update_status_canceled(order_id, new_status, reason)
    await log_status(
        order_id,
        old_status,
        new_status,
        ActorRole.CLIENT.value,
        message.from_user.id,
        f"client canceled (reason): {reason}"
    )

    await state.clear()

    await message.answer(
        f"❌ Замовлення №{order_id} скасовано.\n"
        f"Причина: {reason}",
        reply_markup=after_cancel_kb()
    )

    await notify_admins(
        message.bot,
        render_admin_cancel(order_id, old_status, reason),
        reply_markup=admin_open_order_kb(order_id),
    )

@router.callback_query(F.data.startswith("DESIGN:ADD:"))
async def design_add(cb: CallbackQuery, state: FSMContext):
    try:
        order_id = parse_design_add(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    order = await get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    allowed_statuses = {
        OrderStatus.PAYMENT_REPORTED.value,
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.READY.value,
    }
    if order["status"] not in allowed_statuses:
        await cb.answer("Дизайн можна додати лише після оплати (після завантаження квитанції).", show_alert=True)
        return

    await state.clear()
    await state.update_data(order_id=order_id)
    await state.set_state(DesignFSM.file)

    await cb.message.edit_text(
        f"🎨 Надішліть дизайн-файл для замовлення №{order_id}.\n"
        "Підійде фото або документ (PDF/AI/PSD/CDR тощо)."
    )
    await cb.answer()

@router.message(DesignFSM.file, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def design_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = int(data["order_id"])

    order = await get_order_with_client(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        await state.clear()
        return

    tg_file_id = None
    file_name = None
    mime_type = None

    if message.photo:
        tg_file_id = message.photo[-1].file_id
        file_name = "design.jpg"
        mime_type = "image/jpeg"
    elif message.document:
        tg_file_id = message.document.file_id
        file_name = message.document.file_name
        mime_type = message.document.mime_type

    if not tg_file_id:
        await message.answer("Не вдалося отримати файл. Спробуйте ще раз.")
        return

    await add_order_file(
        order_id=order_id,
        role=FileRole.DESIGN.value,
        tg_file_id=tg_file_id,
        file_name=file_name,
        mime_type=mime_type,
    )

    await log_status(
        order_id,
        order["status"],
        order["status"],
        ActorRole.CLIENT.value,
        message.from_user.id,
        "design file uploaded"
    )

    await state.clear()

    await message.answer(
        f"✅ Дизайн-файл для замовлення №{order_id} отримано.\n"
        "Менеджер перевірить файл. За потреби ми напишемо вам.",
        reply_markup=client_open_order_and_menu_kb(order_id)
    )

    await notify_admins(
        message.bot,
        f"🎨 Отримано дизайн-файл для замовлення №{order_id}.",
        reply_markup=admin_design_files_kb(order_id),
    )
    await notify_admins_copy_message(
        message.bot,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

@router.message(DesignFSM.file)
async def design_wrong_content(message: Message):
    await message.answer("Будь-ласка, надішліть фото або документ з дизайн-файлом.")

@router.callback_query(F.data.startswith("PAY:REPORTED:"))
async def pay_reported(cb: CallbackQuery, state: FSMContext):
    try:
        order_id = parse_pay_reported(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    order = await get_order_with_client(order_id)
    if not order:
        await cb.answer("Замовлення не знайдено.", show_alert=True)
        return

    if order["status"] not in (OrderStatus.CONFIRMED.value, OrderStatus.PAYMENT_REPORTED.value):
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

    order = await get_order_with_client(order_id)
    if not order:
        await message.answer("Замовлення не знайдено.")
        await state.clear()
        return

    tg_file_id = None
    file_name = None
    mime_type = None

    if message.photo:
        tg_file_id = message.photo[-1].file_id
        file_name = "payment.jpg"
        mime_type = "image/jpeg"
    elif message.document:
        tg_file_id = message.document.file_id
        file_name = message.document.file_name
        mime_type = message.document.mime_type

    if not tg_file_id:
        await message.answer("Не вдалося отримати файл. Спробуйте ще раз.")
        return

    await add_order_file(
        order_id=order_id,
        role=FileRole.PAYMENT_PROOF.value,
        tg_file_id=tg_file_id,
        file_name=file_name,
        mime_type=mime_type,
    )

    if order["status"] != OrderStatus.PAYMENT_REPORTED.value:
        old_status = order["status"]
        new_status = OrderStatus.PAYMENT_REPORTED.value

        await update_status_payment_reported(order_id, new_status)
        await log_status(
            order_id,
            old_status,
            new_status,
            ActorRole.CLIENT.value,
            message.from_user.id,
            "payment proof uploaded"
        )

    await state.clear()

    await message.answer(
        f"✅ Квитанцію з оплатою замовлення №{order_id} отримано.\n"
        "Адміністратор перевірить оплату та оновить статус замовлення.\n\n"
        "🎨 Після оплати ви можете надіслати дизайн-файл:",
        reply_markup=after_payment_prompt_kb(order_id)
    )

    await notify_admins(
        message.bot,
        render_admin_payment_received(order, order_id),
        reply_markup=admin_payment_reported_kb(order_id),
    )

    await notify_admins_copy_message(
        message.bot,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

@router.message(PaymentFSM.proof)
async def payment_wrong_content(message: Message):
    await message.answer("Будь-ласка, надішліть фото або документ з квитанцією.")