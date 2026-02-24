from __future__ import annotations

from dataclasses import dataclass

from app.enums import OrderStatus, ActorRole
from app.texts import status_ua
from app.services.orders import admin_set_status_with_timestamp, log_status

@dataclass(frozen=True)
class AdminStatusResult:
    ok: bool
    alert: str
    client_msg: str | None = None

_ALLOWED_TARGETS = {
    OrderStatus.IN_PROGRESS.value,
    OrderStatus.READY.value,
    OrderStatus.DONE.value,
    OrderStatus.CANCELED.value,
}

_ALLOWED_TRANSITIONS = {
    OrderStatus.PAYMENT_REPORTED.value: {OrderStatus.IN_PROGRESS.value, OrderStatus.CANCELED.value},
    OrderStatus.IN_PROGRESS.value: {OrderStatus.READY.value, OrderStatus.DONE.value, OrderStatus.CANCELED.value},
    OrderStatus.READY.value: {OrderStatus.DONE.value, OrderStatus.CANCELED.value},
}

def _build_client_msg(order_id: int, new_status: str) -> str:
    msg = f"ℹ️ Статус замовлення №{order_id} оновлено: {status_ua(new_status)}"
    if new_status == OrderStatus.READY.value:
        msg += "\n\n✅ Менеджер зв’яжеться з вами, щоб уточнити деталі для відправки."
    return msg

async def admin_change_order_status(
    order_id: int,
    old_status: str,
    new_status: str,
    admin_tg_id: int,
) -> AdminStatusResult:
    if new_status not in _ALLOWED_TARGETS:
        return AdminStatusResult(False, "Невідомий статус.")

    if old_status not in _ALLOWED_TRANSITIONS:
        return AdminStatusResult(False, f"Цей статус не підтримує зміну тут: {old_status}")

    if new_status not in _ALLOWED_TRANSITIONS[old_status]:
        return AdminStatusResult(False, f"Не можна: {old_status} ➡️ {new_status}")

    cancel_reason = None
    comment = None
    if new_status == OrderStatus.CANCELED.value:
        cancel_reason = "Скасовано адміністратором"
        comment = cancel_reason

    await admin_set_status_with_timestamp(order_id, new_status, cancel_reason=cancel_reason)
    await log_status(order_id, old_status, new_status, ActorRole.ADMIN.value, admin_tg_id, comment)

    return AdminStatusResult(True, "Оновлено ✅", client_msg=_build_client_msg(order_id, new_status))