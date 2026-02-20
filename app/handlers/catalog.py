from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

CATEGORIES = {
    "Візитки": ["Класичні", "Преміум", "З ламінацією"],
    "Флаєри": ["А6", "А5", "Єврофлаєр"],
    "Наліпки": ["Круглі", "Прямокутні", "Прозорі"],
    "Банери": ["Литий", "Ламінований"],
}

def categories_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=cat, callback_data=f"CAT:{cat}")]
            for cat in CATEGORIES.keys()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="START:MENU")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def services_kb(category: str) -> InlineKeyboardMarkup:
    services = CATEGORIES.get(category, [])
    rows = [[InlineKeyboardButton(text=s, callback_data=f"SVC:{category}:{s}")]
            for s in services]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="CATALOG:OPEN")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def service_confirm_kb(category: str, service: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продовжити", callback_data=f"ORDER:START:{category}:{service}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"CAT:{category}")],
    ])

@router.callback_query(F.data == "CATALOG:OPEN")
async def open_catalog(cb: CallbackQuery):
    await cb.message.edit_text("Оберіть категорію послуг:", reply_markup=categories_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("CAT:"))
async def open_category(cb: CallbackQuery):
    category = cb.data.split("CAT:", 1)[1]
    if category not in CATEGORIES:
        await cb.answer("Невірна категорія", show_alert=True)
        return

    await cb.message.edit_text(
        f"Категорія: {category}\nОберіть послугу:",
        reply_markup=services_kb(category)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("SVC:"))
async def pick_service(cb: CallbackQuery):
    # SVC:<category>:<service>
    parts = cb.data.split(":")
    if len(parts) < 3:
        await cb.answer("Помилка даних.", show_alert=True)
        return

    category = parts[1]
    service = ":".join(parts[2:])

    await cb.message.edit_text(
        f"Обрано послугу:\n{category} → {service}\n\nОформлюємо замовлення?",
        reply_markup=service_confirm_kb(category, service)
    )
    await cb.answer()

@router.callback_query(F.data == "START:MENU")
async def back_to_menu(cb: CallbackQuery):
    await cb.message.edit_text("Головне меню: натисніть /start")
    await cb.answer()