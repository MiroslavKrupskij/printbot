STATUS_UA = {
    "NEW": "Нове",
    "NEED_INFO": "Потрібне уточнення",
    "PRICE_SENT": "Ціну надіслано",
    "CONFIRMED": "Підтверджено",
    "PAYMENT_REPORTED": "Оплачено",
    "IN_PROGRESS": "В роботі",
    "READY": "Готово",
    "DONE": "Виконано",
    "CANCELED": "Скасовано",
}

def status_ua(code: str) -> str:
    return STATUS_UA.get(code, code)