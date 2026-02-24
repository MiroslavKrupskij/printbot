from __future__ import annotations

from typing import Any
from collections.abc import Awaitable, Callable

from app.services.files import list_order_files

async def send_order_files_to_admin_chat(bot, chat_id: int, order_id: int,
    role_filter: str | None = None, reply: Callable[[str], Awaitable[Any]] | None = None) -> int:
    if reply is None:
        async def reply(text: str) -> None:
            await bot.send_message(chat_id, text)

    items = await list_order_files(order_id, role_filter=role_filter)

    if not items:
        if role_filter == "PAYMENT_PROOF":
            await reply(f"Для замовлення №{order_id} квитанцій немає.")
        elif role_filter == "DESIGN":
            await reply(f"Для замовлення №{order_id} дизайн-файлів немає.")
        else:
            await reply(f"Файлів для замовлення №{order_id} немає.")
        return 0

    if role_filter == "PAYMENT_PROOF":
        await reply(f"📄 Квитанція з оплатою • замовлення №{order_id}:")
    elif role_filter == "DESIGN":
        await reply(f"🎨 Дизайн-файли • замовлення №{order_id}:")
    else:
        await reply(f"📎 Файли для замовлення №{order_id}:")

    sent = 0

    for it in items:
        if not isinstance(it, dict):
            continue

        file_role = it.get("role")
        tg_file_id = it.get("tg_file_id")
        mime = (it.get("mime_type") or "").lower()
        name = it.get("file_name") or "file"
        caption = f"{file_role} • {name}"

        if not tg_file_id:
            continue

        try:
            if mime.startswith("image/"):
                await bot.send_photo(chat_id=chat_id, photo=tg_file_id, caption=caption)
            else:
                await bot.send_document(chat_id=chat_id, document=tg_file_id, caption=caption)
            sent += 1
        except Exception:
            try:
                await bot.send_document(chat_id=chat_id, document=tg_file_id, caption=caption)
                sent += 1
            except Exception:
                pass

    return sent