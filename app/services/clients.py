from __future__ import annotations

from app.db import fetchrow, execute

async def get_client_by_id(client_id: int):
    return await fetchrow(
        """
        SELECT client_id, telegram_id, username, full_name, phone
        FROM clients
        WHERE client_id=$1
        """,
        client_id,
    )

async def get_client_by_tg_id(tg_id: int):
    return await fetchrow(
        "SELECT client_id, telegram_id, phone FROM clients WHERE telegram_id=$1",
        tg_id
    )

async def upsert_client_from_contact(
    tg_id: int,
    username: str | None,
    full_name: str,
    phone: str,
):
    row = await get_client_by_tg_id(tg_id)

    if row is None:
        await execute(
            """
            INSERT INTO clients(telegram_id, username, full_name, phone)
            VALUES ($1, $2, $3, $4)
            """,
            tg_id, username, full_name, phone
        )
    else:
        await execute(
            """
            UPDATE clients
            SET username=$2, full_name=$3, phone=$4
            WHERE telegram_id=$1
            """,
            tg_id, username, full_name, phone
        )