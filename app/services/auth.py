from __future__ import annotations

from app.db import fetchrow

async def is_admin(tg_id: int) -> bool:
    row = await fetchrow(
        "SELECT admin_id FROM admins WHERE telegram_id=$1 AND is_active=TRUE",
        tg_id,
    )
    return row is not None

async def get_client_id_by_tg(tg_id: int) -> int | None:
    row = await fetchrow("SELECT client_id FROM clients WHERE telegram_id=$1", tg_id)
    return int(row["client_id"]) if row else None

async def admin_ids() -> list[int]:
    row = await fetchrow("SELECT array_agg(telegram_id) AS ids FROM admins WHERE is_active=TRUE")
    ids = row["ids"] if row and row["ids"] else []
    return [int(x) for x in ids]