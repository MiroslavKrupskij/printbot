from decimal import Decimal
from app.enums import OrderStatus

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

ARTEL_SITE = "https://artel.ua"
ARTEL_PHONE_1 = "+380677100288"
ARTEL_PHONE_2 = "+380957100288"
ARTEL_EMAIL = "print@artel.ua"

ARTEL_ADDRESS = "м. Одеса, вул. Михайла Болтенка, 59"
ARTEL_LAT = 46.461088
ARTEL_LON = 30.720773

def status_ua(code: str) -> str:
    return STATUS_UA.get(code, code)

def format_price(amount) -> str:
    if amount is None:
        return "-"
    if isinstance(amount, Decimal):
        return f"{amount:.2f} грн"
    try:
        return f"{Decimal(str(amount)):.2f} грн"
    except Exception:
        return "-"

def render_order_card(order: dict) -> str:
    order_id = order["order_id"]
    status = order["status"]
    return (
        f"Замовлення №{order_id}\n"
        f"Статус: {status_ua(status)} ({status})\n"
        f"{order['category']} ➡️ {order['service']}\n"
        f"Кількість: {order['quantity']}\n"
        f"Коментар клієнта: {order.get('comment_client') or '-'}\n"
        f"Ціна: {format_price(order.get('price_amount'))}\n"
        f"Коментар до ціни: {order.get('price_comment') or '-'}"
    )

def render_admin_new_order(order_id: int, category: str, service: str, qty: int, comment_client: str | None) -> str:
    return (
        "📦 Нове замовлення!\n"
        f"№{order_id}\n"
        f"{category} ➡️ {service}\n"
        f"Кількість: {qty}\n"
        f"Коментар: {comment_client or '-'}\n"
        f"Статус: {OrderStatus.NEW.value}"
    )

def render_admin_payment_received(order: dict, order_id: int) -> str:
    return (
        "📎 Квитанція з оплатою отримана\n"
        f"Замовлення №{order_id}\n"
        f"{order['category']} ➡️ {order['service']}\n"
        f"Кількість: {order['quantity']}\n"
        f"Ціна: {format_price(order.get('price_amount'))}\n"
        f"Статус: {OrderStatus.PAYMENT_REPORTED.value}"
    )

def render_payment_instructions(order_id: int, price_amount) -> str:
    return (
        "✅ Дякую! Замовлення підтверджено.\n"
        f"Замовлення №{order_id}\n"
        f"Ціна: {format_price(price_amount)}\n\n"
        "💳 Оплата здійснюється на рахунок IBAN: <code>UA453220010000026206349810459</code>\n\n"
        "Після оплати натисніть «Я оплатив(-ла)» і завантажте квитанцію."
    )

def render_admin_need_info(order_id: int, client_tg: int, text: str) -> str:
    return (
        "❓ Уточнення від клієнта\n"
        f"Замовлення №{order_id}\n"
        f"Client TG: {client_tg}\n\n"
        f"{text}"
    )

def render_admin_cancel(order_id: int, old_status: str, reason: str) -> str:
    return (
        f"❌ Клієнт скасував замовлення №{order_id} (було {status_ua(str(old_status))}).\n"
        f"Причина: {reason}"
    )

def render_price_sent_to_client(order_id: int, order: dict, price_amount, price_comment: str | None) -> str:
    return (
        "💰 Розрахунок вартості замовлення готовий!\n"
        f"Замовлення №{order_id}\n"
        f"{order['category']} ➡️ {order['service']}\n"
        f"Кількість: {order['quantity']}\n"
        f"Ціна: {format_price(price_amount)}\n"
        f"Коментар: {(price_comment or '-')}\n\n"
        "Підтвердіть замовлення щоб ми почали роботу."
    )

def render_admin_support_request(row: dict) -> str:
    return (
        "🆘 Звернення підтримки\n"
        f"Request ID: {row.get('request_id', '-')}\n"
        f"Статус: {row.get('status', '-')}\n"
        f"Client TG: {row.get('client_tg', '-')}\n"
        f"Тема: {row.get('topic', '-')}\n\n"
        f"{row.get('message', '')}"
    )

def render_admin_client_info(client: dict) -> str:
    phone = client.get("phone") or "-"
    phone_html = f"<code>{phone}</code>" if phone != "-" else "-"
    name = (client.get("full_name") or "").strip() or (client.get("username") or "-")
    tg = client.get("telegram_id") or "-"
    tg_html = f"<code>{tg}</code>" if tg != "-" else "-"

    return (
        "👤 Інформація про клієнта\n"
        f"Ім’я: {name}\n"
        f"Телефон: {phone_html}\n"
        f"Telegram ID: {tg_html}"
    )

def contacts_text_md() -> str:
    return (
        "📞 *Контакти Artel Print:*\n\n"
        f"☎️ {ARTEL_PHONE_1}\n"
        f"☎️ {ARTEL_PHONE_2}\n"
        f"✉️ {ARTEL_EMAIL}\n\n"
        f"🌐 Сайт: {ARTEL_SITE}"
    )

def help_text_md() -> str:
    return (
        "ℹ️ *Довідка по боту Artel Print*\n\n"
        "🛒 *Каталог послуг*\n"
        "• Оберіть категорію та послугу і вкажіть кількість/коментар.\n"
        "• Менеджер надішле розрахунок ціни, після чого оплатіть замовлення та надішліть дизайн-файл.\n\n"
        "📋 *Мої замовлення*\n"
        "• Перегляд ваших замовлень та поточного статусу.\n\n"
        "🆘 *Підтримка*\n"
        "• Напишіть питання — менеджер відповість.\n\n"
        f"📍 Адреса: {ARTEL_ADDRESS}\n"
        f"🌐 Сайт: {ARTEL_SITE}"
    )

def location_text_md() -> str:
    return (
        "📍 *Наше місцезнаходження*\n\n"
        f"{ARTEL_ADDRESS}\n\n"
        f"🌐 {ARTEL_SITE}"
    )

def support_topic_prompt() -> str:
    return (
        "Підтримка\n\n"
        "Вкажіть тему звернення одним коротким повідомленням («Питання по замовленню» тощо)."
    )

def support_message_prompt() -> str:
    return "Опишіть детально проблему одним повідомленням."