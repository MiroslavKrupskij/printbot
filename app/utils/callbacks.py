from __future__ import annotations

class CallbackParseError(ValueError):
    pass

def _split(data: str) -> list[str]:
    if not data or ":" not in data:
        raise CallbackParseError("Некоректний callback_data.")
    return data.split(":")

def last_int(data: str) -> int:
    p = _split(data)
    try:
        return int(p[-1])
    except Exception as e:
        raise CallbackParseError("Некоректний id у callback_data.") from e

def parse_admin_list(data: str) -> str:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "LIST":
        raise CallbackParseError("Очікував ADMIN:LIST:{STATUS}")
    return p[2]

def parse_admin_open(data: str) -> int:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "OPEN":
        raise CallbackParseError("Очікував ADMIN:OPEN:{id}")
    try:
        return int(p[2])
    except Exception as e:
        raise CallbackParseError("Некоректний order_id.") from e

def parse_admin_client(data: str) -> int:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "CLIENT":
        raise CallbackParseError("Очікував ADMIN:CLIENT:{id}")
    try:
        return int(p[2])
    except Exception as e:
        raise CallbackParseError("Некоректний order_id.") from e

def parse_admin_client_msg(data: str) -> int:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "CLIENT_MSG":
        raise CallbackParseError("Очікував ADMIN:CLIENT_MSG:{id}")
    try:
        return int(p[2])
    except Exception as e:
        raise CallbackParseError("Некоректний order_id.") from e

def parse_admin_need_close(data: str) -> int:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "NEED_CLOSE":
        raise CallbackParseError("Очікував ADMIN:NEED_CLOSE:{id}")
    try:
        return int(p[2])
    except Exception as e:
        raise CallbackParseError("Некоректний order_id.") from e

def parse_admin_need_reply(data: str) -> int:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "NEED_REPLY":
        raise CallbackParseError("Очікував ADMIN:NEED_REPLY:{id}")
    try:
        return int(p[2])
    except Exception as e:
        raise CallbackParseError("Некоректний order_id.") from e

def parse_admin_set_price(data: str) -> int:
    p = _split(data)
    if len(p) != 3 or p[0] != "ADMIN" or p[1] != "SET_PRICE":
        raise CallbackParseError("Очікував ADMIN:SET_PRICE:{id}")
    try:
        return int(p[2])
    except Exception as e:
        raise CallbackParseError("Некоректний order_id.") from e

def parse_admin_status(data: str) -> tuple[int, str]:
    p = _split(data)
    if len(p) != 4 or p[0] != "ADMIN" or p[1] != "STATUS":
        raise CallbackParseError("Очікував ADMIN:STATUS:{id}:{STATUS}")
    try:
        return int(p[2]), p[3]
    except Exception as e:
        raise CallbackParseError("Некоректний payload status.") from e

def parse_admin_files(data: str) -> tuple[int, str | None]:
    p = _split(data)
    if len(p) < 3 or p[0] != "ADMIN" or p[1] != "FILES":
        raise CallbackParseError("Очікував ADMIN:FILES:...")

    if len(p) == 3:
        try:
            return int(p[2]), None
        except Exception as e:
            raise CallbackParseError("Некоректний order_id.") from e

    if len(p) == 4 and p[2] in {"PAYMENT", "DESIGN"}:
        try:
            order_id = int(p[3])
        except Exception as e:
            raise CallbackParseError("Некоректний order_id.") from e
        role_filter = "PAYMENT_PROOF" if p[2] == "PAYMENT" else "DESIGN"
        return order_id, role_filter

    raise CallbackParseError("Некоректний формат ADMIN:FILES.")

def parse_admin_support_action(data: str) -> tuple[str, int]:
    p = _split(data)
    if len(p) != 4 or p[0] != "ADMIN" or p[1] != "SUPPORT":
        raise CallbackParseError("Очікував ADMIN:SUPPORT:{ACTION}:{id}")
    action = p[2]
    try:
        request_id = int(p[3])
    except Exception as e:
        raise CallbackParseError("Некоректний request_id.") from e
    return action, request_id

def parse_order_start(data: str) -> tuple[int, int]:
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "ORDER" or parts[1] != "START":
        raise CallbackParseError("Bad ORDER:START payload")
    try:
        return int(parts[2]), int(parts[3])
    except ValueError as e:
        raise CallbackParseError("Bad ORDER:START ids") from e

def parse_orders_open(data: str) -> int:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "ORDERS" or parts[1] != "OPEN":
        raise CallbackParseError("Bad ORDERS:OPEN payload")
    try:
        return int(parts[2])
    except ValueError as e:
        raise CallbackParseError("Bad order_id") from e

def parse_order_action_1id(data: str, prefix: str) -> int:
    parts = data.split(":")
    want = prefix.split(":")
    if len(parts) != len(want) + 1 or parts[:len(want)] != want:
        raise CallbackParseError(f"Bad {prefix} payload")
    try:
        return int(parts[-1])
    except ValueError as e:
        raise CallbackParseError("Bad order_id") from e

def parse_order_confirm(data: str) -> int:
    return parse_order_action_1id(data, "ORDER:CONFIRM")

def parse_order_need_info(data: str) -> int:
    return parse_order_action_1id(data, "ORDER:NEED_INFO")

def parse_order_continue(data: str) -> int:
    return parse_order_action_1id(data, "ORDER:CONTINUE")

def parse_order_cancel(data: str) -> int:
    return parse_order_action_1id(data, "ORDER:CANCEL")

def parse_design_add(data: str) -> int:
    return parse_order_action_1id(data, "DESIGN:ADD")

def parse_pay_reported(data: str) -> int:
    return parse_order_action_1id(data, "PAY:REPORTED")

def cb_client_menu() -> str:
    return "CLIENT:MENU"

def cb_orders_my() -> str:
    return "ORDERS:MY"

def cb_orders_open(order_id: int) -> str:
    return f"ORDERS:OPEN:{int(order_id)}"

def cb_catalog_back(cat_id: int) -> str:
    return f"CAT:{int(cat_id)}"

def cb_order_confirm(order_id: int) -> str:
    return f"ORDER:CONFIRM:{int(order_id)}"

def cb_order_need_info(order_id: int) -> str:
    return f"ORDER:NEED_INFO:{int(order_id)}"

def cb_order_continue(order_id: int) -> str:
    return f"ORDER:CONTINUE:{int(order_id)}"

def cb_order_cancel(order_id: int) -> str:
    return f"ORDER:CANCEL:{int(order_id)}"

def cb_pay_reported(order_id: int) -> str:
    return f"PAY:REPORTED:{int(order_id)}"

def cb_design_add(order_id: int) -> str:
    return f"DESIGN:ADD:{int(order_id)}"

def cb_admin_menu() -> str:
    return "ADMIN:MENU"

def cb_admin_list(status: str) -> str:
    return f"ADMIN:LIST:{status}"

def cb_admin_open(order_id: int) -> str:
    return f"ADMIN:OPEN:{int(order_id)}"

def cb_admin_client(order_id: int) -> str:
    return f"ADMIN:CLIENT:{int(order_id)}"

def cb_admin_client_msg(order_id: int) -> str:
    return f"ADMIN:CLIENT_MSG:{int(order_id)}"

def cb_admin_set_price(order_id: int) -> str:
    return f"ADMIN:SET_PRICE:{int(order_id)}"

def cb_admin_need_reply(order_id: int) -> str:
    return f"ADMIN:NEED_REPLY:{int(order_id)}"

def cb_admin_need_close(order_id: int) -> str:
    return f"ADMIN:NEED_CLOSE:{int(order_id)}"

def cb_admin_status(order_id: int, status: str) -> str:
    return f"ADMIN:STATUS:{int(order_id)}:{status}"

def cb_admin_files(order_id: int, kind: str | None = None) -> str:
    if kind is None:
        return f"ADMIN:FILES:{int(order_id)}"
    if kind not in {"PAYMENT", "DESIGN"}:
        raise ValueError("kind must be None | 'PAYMENT' | 'DESIGN'")
    return f"ADMIN:FILES:{kind}:{int(order_id)}"

def cb_admin_support_list() -> str:
    return "ADMIN:SUPPORT:LIST"

def cb_admin_support_open(request_id: int) -> str:
    return f"ADMIN:SUPPORT:OPEN:{int(request_id)}"

def cb_admin_support_reply(request_id: int) -> str:
    return f"ADMIN:SUPPORT:REPLY:{int(request_id)}"

def cb_admin_support_close(request_id: int) -> str:
    return f"ADMIN:SUPPORT:CLOSE:{int(request_id)}"

def cb_catalog_open() -> str:
    return "CATALOG:OPEN"

def cb_cat(cat_id: int) -> str:
    return f"CAT:{int(cat_id)}"

def cb_svc(cat_id: int, svc_id: int) -> str:
    return f"SVC:{int(cat_id)}:{int(svc_id)}"

def cb_svc_page(cat_id: int, page: int) -> str:
    return f"SVC_PAGE:{int(cat_id)}:{int(page)}"

def cb_ignore() -> str:
    return "IGNORE"

def cb_start_menu() -> str:
    return "START:MENU"

def cb_contacts_open() -> str:
    return "CONTACTS:OPEN"

def cb_location_open() -> str:
    return "LOCATION:OPEN"

def cb_help_open() -> str:
    return "HELP:OPEN"

def cb_order_start(cat_id: int, svc_id: int) -> str:
    return f"ORDER:START:{int(cat_id)}:{int(svc_id)}"

def parse_cat(data: str) -> int:
    parts = data.split(":")
    if len(parts) != 2 or parts[0] != "CAT":
        raise CallbackParseError("Bad CAT payload")
    try:
        return int(parts[1])
    except ValueError as e:
        raise CallbackParseError("Bad cat_id") from e

def parse_svc(data: str) -> tuple[int, int]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "SVC":
        raise CallbackParseError("Bad SVC payload")
    try:
        return int(parts[1]), int(parts[2])
    except ValueError as e:
        raise CallbackParseError("Bad svc ids") from e

def parse_svc_page(data: str) -> tuple[int, int]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "SVC_PAGE":
        raise CallbackParseError("Bad SVC_PAGE payload")
    try:
        return int(parts[1]), int(parts[2])
    except ValueError as e:
        raise CallbackParseError("Bad page ids") from e

def cb_support_open() -> str:
    return "SUPPORT:OPEN"

def parse_support_open(data: str) -> None:
    if data != "SUPPORT:OPEN":
        raise CallbackParseError("Bad SUPPORT:OPEN payload")