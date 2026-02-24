from __future__ import annotations

from decimal import Decimal

from app.db import fetchrow, execute
from app.enums import OrderStatus

_STATUS_TO_TIMEFIELD = {
    OrderStatus.IN_PROGRESS.value: "in_progress_at",
    OrderStatus.READY.value: "ready_at",
    OrderStatus.DONE.value: "done_at",
    OrderStatus.CANCELED.value: "canceled_at",
}

async def get_order_with_client(order_id: int):
    return await fetchrow(
        """
        SELECT o.order_id, o.client_id, o.status, o.price_amount, o.category, o.service, o.quantity,
               c.telegram_id AS client_tg
        FROM orders o
        JOIN clients c ON c.client_id = o.client_id
        WHERE o.order_id = $1
        """,
        order_id,
    )

async def get_admin_order(order_id: int):
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

async def log_status(order_id: int, old_status: str | None, new_status: str,
                     role: str, tg_id: int, comment: str | None,):
    await execute(
        """
        INSERT INTO order_status_history
            (order_id, old_status, new_status, changed_by_role, changed_by_telegram_id, comment)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        order_id,
        old_status,
        new_status,
        role,
        tg_id,
        comment,
    )

async def create_order(
    client_id: int,
    category: str,
    service: str,
    quantity: int,
    comment_client: str | None,
) -> int:
    row = await fetchrow(
        """
        INSERT INTO orders (client_id, category, service, quantity, comment_client, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING order_id
        """,
        client_id, category, service, quantity, comment_client, OrderStatus.NEW.value
    )
    return int(row["order_id"])

async def list_client_order_ids(client_id: int, limit: int = 10) -> list[int]:
    row = await fetchrow(
        """
        SELECT array_agg(order_id ORDER BY created_at DESC) AS ids
        FROM orders
        WHERE client_id=$1
        """,
        client_id
    )
    ids = row["ids"] if row and row["ids"] else []
    ids = [int(x) for x in ids]
    return ids[:limit]

async def get_client_order(order_id: int, client_id: int):
    return await fetchrow(
        """
        SELECT order_id, category, service, quantity, comment_client, status, price_amount, price_comment
        FROM orders
        WHERE order_id=$1 AND client_id=$2
        """,
        order_id, client_id
    )

async def update_status_simple(order_id: int, new_status: str):
    await execute(
        "UPDATE orders SET status=$2 WHERE order_id=$1",
        order_id, new_status
    )

async def update_status_confirmed(order_id: int, new_status: str):
    await execute(
        "UPDATE orders SET status=$2, confirmed_at=now() WHERE order_id=$1",
        order_id, new_status
    )

async def update_status_canceled(order_id: int, new_status: str, reason: str):
    await execute(
        "UPDATE orders SET status=$2, canceled_at=now(), cancel_reason=$3 WHERE order_id=$1",
        order_id, new_status, reason
    )

async def update_status_payment_reported(order_id: int, new_status: str):
    await execute(
        "UPDATE orders SET status=$2, payment_reported_at=now() WHERE order_id=$1",
        order_id, new_status
    )

async def list_order_ids_by_status(status: str) -> list[int]:
    row = await fetchrow(
        """
        SELECT array_agg(order_id ORDER BY created_at DESC) AS ids
        FROM orders
        WHERE status=$1
        """,
        status,
    )
    ids = row["ids"] if row and row["ids"] else []
    return [int(x) for x in ids]

async def set_price_and_mark_price_sent(order_id: int, price_amount: Decimal,
    price_comment: str | None,) -> str:
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

    return new_status

async def admin_set_status_with_timestamp(order_id: int, new_status: str,
                                          cancel_reason: str | None = None,):
    time_field = _STATUS_TO_TIMEFIELD.get(new_status)
    if not time_field:
        raise ValueError(f"Unsupported status for timestamp: {new_status}")

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
            cancel_reason or "Скасовано адміністратором",
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