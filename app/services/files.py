from __future__ import annotations

import json
from typing import Any

from app.db import fetchrow, execute

def _normalize_json_items(value: Any) -> list[dict]:
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return []
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for it in value:
        if isinstance(it, str):
            try:
                it = json.loads(it)
            except Exception:
                continue
        if isinstance(it, dict):
            out.append(it)
    return out

async def list_order_files(order_id: int, role_filter: str | None = None) -> list[dict]:
    if role_filter is None:
        row = await fetchrow(
            """
            SELECT json_agg(t ORDER BY t.created_at ASC) AS items
            FROM (
                SELECT role, tg_file_id, file_name, mime_type, created_at
                FROM order_files
                WHERE order_id=$1
                ORDER BY created_at ASC
            ) t
            """,
            order_id,
        )
    else:
        row = await fetchrow(
            """
            SELECT json_agg(t ORDER BY t.created_at ASC) AS items
            FROM (
                SELECT role, tg_file_id, file_name, mime_type, created_at
                FROM order_files
                WHERE order_id=$1 AND role=$2
                ORDER BY created_at ASC
            ) t
            """,
            order_id,
            role_filter,
        )

    return _normalize_json_items(row["items"] if row else None)

async def add_order_file(
    order_id: int,
    role: str,
    tg_file_id: str,
    file_name: str | None,
    mime_type: str | None,
):
    await execute(
        """
        INSERT INTO order_files(order_id, role, tg_file_id, file_name, mime_type)
        VALUES ($1, $2, $3, $4, $5)
        """,
        order_id, role, tg_file_id, file_name, mime_type
    )