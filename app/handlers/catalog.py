from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.handlers.start import main_menu_kb
from app.services.catalog_service import get_categories, get_category_name, get_services, is_valid_service
from app.utils.callbacks import (
    CallbackParseError, cb_cat, cb_catalog_open, cb_ignore, cb_start_menu,
    cb_svc, cb_svc_page, parse_cat, parse_svc, parse_svc_page, cb_order_start,
)

router = Router()

PAGE_SIZE = 8
CATS_LIST = get_categories()

def categories_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=cat_name, callback_data=cb_cat(cat_id))]
        for cat_id, cat_name in enumerate(CATS_LIST)
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_start_menu())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _services_page(cat_id: int, page: int) -> tuple[list[str], int]:
    services = get_services(cat_id)
    if not services:
        return [], 0

    total_pages = (len(services) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    return services[start:end], total_pages

def services_kb(cat_id: int, page: int = 0) -> InlineKeyboardMarkup:
    services_slice, total_pages = _services_page(cat_id, page)
    services_all = get_services(cat_id)

    rows: list[list[InlineKeyboardButton]] = []
    for svc_id, s in enumerate(services_all):
        if s in services_slice:
            rows.append([InlineKeyboardButton(text=s, callback_data=cb_svc(cat_id, svc_id))])

    if total_pages > 1:
        nav_row: list[InlineKeyboardButton] = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=cb_svc_page(cat_id, page - 1)))
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=cb_ignore()))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="➡️", callback_data=cb_svc_page(cat_id, page + 1)))
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_catalog_open())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def service_confirm_kb(cat_id: int, svc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продовжити", callback_data=cb_order_start(cat_id, svc_id))],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_cat(cat_id))],
    ])

@router.callback_query(F.data == "CATALOG:OPEN")
async def open_catalog(cb: CallbackQuery):
    await cb.message.edit_text("🖨 Оберіть категорію послуг:", reply_markup=categories_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("CAT:"))
async def open_category(cb: CallbackQuery):
    try:
        cat_id = parse_cat(cb.data)
    except CallbackParseError:
        await cb.answer("Невірна категорія", show_alert=True)
        return

    category = get_category_name(cat_id)
    if category is None:
        await cb.answer("Невірна категорія", show_alert=True)
        return

    await cb.message.edit_text(
        f"Категорія: {category}\nОберіть послугу:",
        reply_markup=services_kb(cat_id, page=0)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("SVC_PAGE:"))
async def open_category_page(cb: CallbackQuery):
    try:
        cat_id, page = parse_svc_page(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    category = get_category_name(cat_id)
    if category is None:
        await cb.answer("Невірна категорія", show_alert=True)
        return

    await cb.message.edit_text(
        f"Категорія: {category}\nОберіть послугу:",
        reply_markup=services_kb(cat_id, page=page)
    )
    await cb.answer()

@router.callback_query(F.data == "IGNORE")
async def ignore_cb(cb: CallbackQuery):
    await cb.answer()

@router.callback_query(F.data.startswith("SVC:"))
async def pick_service(cb: CallbackQuery):
    try:
        cat_id, svc_id = parse_svc(cb.data)
    except CallbackParseError:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    category = get_category_name(cat_id)
    if category is None or not is_valid_service(cat_id, svc_id):
        await cb.answer("Невірні дані послуги.", show_alert=True)
        return

    services = get_services(cat_id)
    if svc_id < 0 or svc_id >= len(services):
        await cb.answer("Невірні дані послуги.", show_alert=True)
        return

    service = services[svc_id]

    await cb.message.edit_text(
        f"🔖 Обрано послугу:\n{category} ➡️ {service}\n\n📦 Оформлюємо замовлення?",
        reply_markup=service_confirm_kb(cat_id, svc_id)
    )
    await cb.answer()

@router.callback_query(F.data == "START:MENU")
async def back_to_menu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "🔸 Меню користувача:",
        reply_markup=main_menu_kb()
    )