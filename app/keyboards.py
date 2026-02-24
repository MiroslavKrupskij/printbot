from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.enums import OrderStatus
from app.utils.callbacks import (
    cb_client_menu, cb_orders_my, cb_orders_open, cb_catalog_back,
    cb_order_confirm, cb_order_need_info, cb_order_continue, cb_order_cancel,
    cb_pay_reported, cb_design_add, cb_admin_menu, cb_admin_list, cb_admin_open,
    cb_admin_client, cb_admin_client_msg, cb_admin_set_price, cb_admin_need_reply,
    cb_admin_need_close, cb_admin_status, cb_admin_files, cb_admin_support_list,
    cb_admin_support_open, cb_admin_support_reply, cb_admin_support_close, cb_support_open,
)

def main_menu_kb() -> InlineKeyboardMarkup:
    from app.utils.callbacks import (
        cb_catalog_open, cb_orders_my,
        cb_contacts_open, cb_location_open, cb_help_open,
    )

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Каталог послуг", callback_data=cb_catalog_open())],
        [InlineKeyboardButton(text="📋 Мої замовлення", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="🆘 Підтримка", callback_data=cb_support_open())],
        [InlineKeyboardButton(text="📞 Наші контакти", callback_data=cb_contacts_open())],
        [InlineKeyboardButton(text="📍 Наше місцезнаходження", callback_data=cb_location_open())],
        [InlineKeyboardButton(text="ℹ️ Допомога", callback_data=cb_help_open())],
    ])

def back_to_menu_kb() -> InlineKeyboardMarkup:
    from app.utils.callbacks import cb_client_menu
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_client_menu())]
    ])

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Надіслати номер телефону", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def persistent_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="☰ Меню")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def price_confirm_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтверджую", callback_data=cb_order_confirm(order_id))],
        [InlineKeyboardButton(text="❓ Потрібне уточнення", callback_data=cb_order_need_info(order_id))],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_order_cancel(order_id))],
    ])

def payment_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Я оплатив(-ла)", callback_data=cb_pay_reported(order_id))],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_order_cancel(order_id))],
    ])

def support_request_kb(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Відповісти", callback_data=cb_admin_support_reply(request_id))],
        [InlineKeyboardButton(text="✅ Закрити", callback_data=cb_admin_support_close(request_id))],
    ])

def qty_cancel_kb(cat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_catalog_back(cat_id))],
    ])

def my_orders_kb(order_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Замовлення №{oid}", callback_data=cb_orders_open(oid))]
        for oid in order_ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def order_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ До списку", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def add_design_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Додати дизайн-файл", callback_data=cb_design_add(order_id))],
        [InlineKeyboardButton(text="⬅️ До списку", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def after_payment_prompt_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Додати дизайн-файл", callback_data=cb_design_add(order_id))],
        [InlineKeyboardButton(text=f"📦 Відкрити замовлення №{order_id}", callback_data=cb_orders_open(order_id))],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def confirmed_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Я оплатив(-ла)", callback_data=cb_pay_reported(order_id))],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_order_cancel(order_id))],
        [InlineKeyboardButton(text="⬅️ До списку", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def admin_need_info_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Відповісти", callback_data=cb_admin_need_reply(order_id))],
        [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=cb_admin_open(order_id))],
    ])

def admin_payment_reported_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплату підтверджено", callback_data=cb_admin_status(order_id, "IN_PROGRESS"))],
        [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=cb_admin_open(order_id))],
    ])

def client_created_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Мої замовлення", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def client_empty_orders_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())]
    ])

def order_price_sent_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтверджую", callback_data=cb_order_confirm(order_id))],
        [InlineKeyboardButton(text="❓ Потрібне уточнення", callback_data=cb_order_need_info(order_id))],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_order_cancel(order_id))],
        [InlineKeyboardButton(text="⬅️ До списку", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def order_need_info_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продовжити", callback_data=cb_order_continue(order_id))],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_order_cancel(order_id))],
        [InlineKeyboardButton(text="⬅️ До списку", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def cancel_reason_back_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_orders_open(order_id))],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def after_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Мої замовлення", callback_data=cb_orders_my())],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def client_menu_only_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())]
    ])

def client_open_order_and_menu_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 Відкрити замовлення №{order_id}", callback_data=cb_orders_open(order_id))],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_client_menu())],
    ])

def admin_open_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=cb_admin_open(order_id))]
    ])

def admin_design_files_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Показати дизайн-файли", callback_data=cb_admin_files(order_id, "DESIGN"))],
        [InlineKeyboardButton(text=f"📦 Відкрити №{order_id}", callback_data=cb_admin_open(order_id))],
    ])

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Нові замовлення", callback_data=cb_admin_list("NEW"))],
        [InlineKeyboardButton(text="❓ Потребують уточнення", callback_data=cb_admin_list("NEED_INFO"))],
        [InlineKeyboardButton(text="💳 Оплачені замовлення", callback_data=cb_admin_list("PAYMENT_REPORTED"))],
        [InlineKeyboardButton(text="🛠 Замовлення, які виконуються", callback_data=cb_admin_list("IN_PROGRESS"))],
        [InlineKeyboardButton(text="✅ Готові замовлення", callback_data=cb_admin_list("READY"))],
        [InlineKeyboardButton(text="🏁 Завершені (DONE)", callback_data=cb_admin_list("DONE"))],
        [InlineKeyboardButton(text="❌ Скасовані (CANCELED)", callback_data=cb_admin_list("CANCELED"))],
        [InlineKeyboardButton(text="🆘 Заявки в підтримку", callback_data=cb_admin_support_list())],
    ])

def orders_list_kb(order_ids: list[int], back_to_menu: bool = True) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"Замовлення №{oid}", callback_data=cb_admin_open(oid))]
            for oid in order_ids]
    if back_to_menu:
        rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_admin_menu())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_back_kb(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=target)]
    ])

def order_actions_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="👤 Інфо про клієнта", callback_data=cb_admin_client(order_id))]
    ]

    if status == OrderStatus.NEW.value:
        rows.append([InlineKeyboardButton(text="💰 Встановити ціну", callback_data=cb_admin_set_price(order_id))])

    if status == OrderStatus.NEED_INFO.value:
        rows.append([InlineKeyboardButton(text="💬 Відповісти клієнту", callback_data=cb_admin_need_reply(order_id))])
        rows.append([InlineKeyboardButton(text="✅ Уточнення надано", callback_data=cb_admin_need_close(order_id))])

    if status == OrderStatus.PAYMENT_REPORTED.value:
        rows.append([InlineKeyboardButton(text="📄 Показати квитанцію з оплатою", callback_data=cb_admin_files(order_id, "PAYMENT"))])
        rows.append([InlineKeyboardButton(text="🎨 Показати дизайн-файли", callback_data=cb_admin_files(order_id, "DESIGN"))])
        rows.append([InlineKeyboardButton(text="✅ Оплату підтверджено", callback_data=cb_admin_status(order_id, "IN_PROGRESS"))])
        rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_admin_status(order_id, "CANCELED"))])

    if status == OrderStatus.IN_PROGRESS.value:
        rows.append([InlineKeyboardButton(text="📄 Показати квитанцію з оплатою", callback_data=cb_admin_files(order_id, "PAYMENT"))])
        rows.append([InlineKeyboardButton(text="🎨 Показати дизайн-файли", callback_data=cb_admin_files(order_id, "DESIGN"))])
        rows.append([InlineKeyboardButton(text="✅ Готово", callback_data=cb_admin_status(order_id, "READY"))])
        rows.append([InlineKeyboardButton(text="🏁 Завершити", callback_data=cb_admin_status(order_id, "DONE"))])
        rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_admin_status(order_id, "CANCELED"))])

    if status == OrderStatus.READY.value:
        rows.append([InlineKeyboardButton(text="📄 Показати квитанцію з оплатою", callback_data=cb_admin_files(order_id, "PAYMENT"))])
        rows.append([InlineKeyboardButton(text="🎨 Показати дизайн-файли", callback_data=cb_admin_files(order_id, "DESIGN"))])
        rows.append([InlineKeyboardButton(text="🏁 Завершити", callback_data=cb_admin_status(order_id, "DONE"))])
        rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=cb_admin_status(order_id, "CANCELED"))])

    rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_admin_menu())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def support_list_kb(request_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"Звернення №{rid}", callback_data=cb_admin_support_open(rid))]
            for rid in request_ids]
    rows.append([InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_admin_menu())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def support_actions_kb(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Відповісти", callback_data=cb_admin_support_reply(request_id))],
        [InlineKeyboardButton(text="✅ Закрити", callback_data=cb_admin_support_close(request_id))],
        [InlineKeyboardButton(text="⬅️ До списку", callback_data=cb_admin_support_list())],
    ])

def admin_after_message_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Інфо про клієнта", callback_data=cb_admin_client(order_id))],
        [InlineKeyboardButton(text=f"📦 Відкрити замовлення №{order_id}", callback_data=cb_admin_open(order_id))],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_admin_menu())],
    ])

def admin_client_info_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написати клієнту", callback_data=cb_admin_client_msg(order_id))],
        [InlineKeyboardButton(text=f"📦 Відкрити замовлення №{order_id}", callback_data=cb_admin_open(order_id))],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data=cb_admin_menu())],
    ])