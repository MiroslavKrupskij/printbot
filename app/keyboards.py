from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Надіслати номер телефону", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )