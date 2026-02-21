from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

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
        [InlineKeyboardButton(text="✅ Підтверджую", callback_data=f"ORDER:CONFIRM:{order_id}")],
        [InlineKeyboardButton(text="❓ Потрібне уточнення", callback_data=f"ORDER:NEED_INFO:{order_id}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ORDER:CANCEL:{order_id}")],
    ])

def payment_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Я оплатив(-ла)", callback_data=f"PAY:REPORTED:{order_id}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=f"ORDER:CANCEL:{order_id}")],
    ])

def support_request_kb(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Відповісти", callback_data=f"ADMIN:SUPPORT:REPLY:{request_id}")],
        [InlineKeyboardButton(text="✅ Закрити", callback_data=f"ADMIN:SUPPORT:CLOSE:{request_id}")],
    ])