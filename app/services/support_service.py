from __future__ import annotations

from app.db import fetchrow, execute
from app.enums import SupportStatus
from app.services.auth import admin_ids

async def close_support_with_reply(bot, request_id: int, reply_text: str) -> str:
    row = await fetchrow(
        """
        SELECT sr.request_id, sr.status, sr.topic,
               c.telegram_id AS client_tg
        FROM support_requests sr
        JOIN clients c ON c.client_id = sr.client_id
        WHERE sr.request_id=$1
        """,
        request_id,
    )
    if not row:
        return f"Звернення №{request_id} не знайдено."

    if row["status"] != "OPEN":
        return f"Звернення №{request_id} вже закрите."

    client_tg = int(row["client_tg"])

    await bot.send_message(
        client_tg,
        "📩 Відповідь підтримки\n"
        f"Звернення №{request_id}\n"
        f"Тема: {row['topic']}\n\n"
        f"{reply_text}",
    )

    await execute(
        "UPDATE support_requests SET status='CLOSED', closed_at=now() WHERE request_id=$1",
        request_id,
    )
    return f"✅ Відповідь на звернення №{request_id} надіслано. Звернення закрито."

async def close_support_without_reply(request_id: int) -> str:
    row = await fetchrow(
        "SELECT request_id, status FROM support_requests WHERE request_id=$1",
        request_id,
    )
    if not row:
        return "Звернення не знайдено."
    if row["status"] != "OPEN":
        return "Воно вже закрите."

    await execute(
        "UPDATE support_requests SET status='CLOSED', closed_at=now() WHERE request_id=$1",
        request_id,
    )
    return f"✅ Звернення №{request_id} закрито."

async def list_open_support_request_ids(limit: int = 50) -> list[int]:
    row = await fetchrow(
        """
        SELECT array_agg(request_id ORDER BY created_at DESC) AS ids
        FROM support_requests
        WHERE status='OPEN'
        """,
    )
    ids = row["ids"] if row and row["ids"] else []
    ids = [int(x) for x in ids]
    return ids[:limit]

async def get_support_request_with_client(request_id: int):
    return await fetchrow(
        """
        SELECT sr.request_id, sr.client_id, sr.topic, sr.message, sr.status, sr.created_at,
               c.telegram_id, c.username, c.full_name, c.phone
        FROM support_requests sr
        JOIN clients c ON c.client_id = sr.client_id
        WHERE sr.request_id=$1
        """,
        request_id,
    )

async def get_support_request(request_id: int):
    return await fetchrow(
        """
        SELECT request_id, client_id, topic, message, status, created_at
        FROM support_requests
        WHERE request_id=$1
        """,
        request_id,
    )

async def create_support_request(client_id: int, topic: str, message: str) -> int:
    row = await fetchrow(
        """
        INSERT INTO support_requests (client_id, topic, message, status)
        VALUES ($1, $2, $3, $4)
        RETURNING request_id
        """,
        client_id, topic, message, SupportStatus.OPEN.value
    )
    return int(row["request_id"])

async def notify_admins_about_support(bot, request_id: int, client_tg: int, topic: str, text: str, reply_markup):
    for admin_tg in await admin_ids():
        try:
            await bot.send_message(
                admin_tg,
                "🆘 Нове звернення підтримки\n"
                f"Request ID: {request_id}\n"
                f"Client TG: {client_tg}\n"
                f"Тема: {topic}\n\n"
                f"{text}",
                reply_markup=reply_markup
            )
        except Exception:
            pass