from __future__ import annotations

from app.enums import ActorRole, OrderStatus
from app.texts import status_ua
from app.services.orders import get_admin_order, log_status, update_status_simple

async def send_manager_message_to_client(
    *,
    bot,
    order_id: int,
    admin_tg_id: int,
    text: str,
) -> tuple[bool, str]:
    order = await get_admin_order(order_id)
    if not order:
        return False, "Замовлення не знайдено."

    client_tg = int(order["client_tg"])

    try:
        await bot.send_message(
            client_tg,
            f"✉️ Повідомлення від менеджера щодо замовлення №{order_id}:\n\n{text}",
        )
    except Exception:
        return False, "Не вдалося надіслати повідомлення клієнту (Telegram помилка)."

    await log_status(
        order_id=order_id,
        old_status=order["status"],
        new_status=order["status"],
        role=ActorRole.ADMIN.value,
        tg_id=admin_tg_id,
        comment=f"admin message to client: {text}",
    )

    return True, "✅ Повідомлення надіслано клієнту."

async def close_need_info(
    *,
    bot,
    order_id: int,
    admin_tg_id: int,
    reply_text: str | None,
) -> tuple[bool, str, str | None]:
    order = await get_admin_order(order_id)
    if not order:
        return False, "Замовлення не знайдено.", None

    if order["status"] != OrderStatus.NEED_INFO.value:
        return False, "Це замовлення вже не у статусі NEED_INFO.", None

    client_tg = int(order["client_tg"])

    if reply_text is not None:
        try:
            await bot.send_message(
                client_tg,
                f"💬 Відповідь менеджера по замовленню №{order_id}:\n\n{reply_text}",
            )
        except Exception:
            return False, "Не вдалося надіслати відповідь клієнту (Telegram помилка).", None

    old_status = order["status"]
    next_status = OrderStatus.PRICE_SENT.value if order["price_amount"] is not None else OrderStatus.NEW.value

    await update_status_simple(order_id, next_status)

    await log_status(
        order_id=order_id,
        old_status=old_status,
        new_status=next_status,
        role=ActorRole.ADMIN.value,
        tg_id=admin_tg_id,
        comment=("NEED_INFO answered: " + reply_text) if reply_text else "closed NEED_INFO",
    )

    try:
        await bot.send_message(
            client_tg,
            f"✅ Уточнення враховано. Статус замовлення №{order_id}: {status_ua(next_status)}",
        )
    except Exception:
        pass

    alert = "Відповідь надіслано ✅" if reply_text else "Уточнення закрито ✅"
    return True, alert, next_status