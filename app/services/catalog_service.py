from __future__ import annotations

from typing import Optional

CATEGORIES: dict[str, list[str]] = {
    "Рекламна і бізнес поліграфія": [
        "Візитки",
        "Флаєри та листівки",
        "Буклети",
        "Наліпки, стікери",
        "Брошури",
        "Блокноти",
        "Щотижневики",
        "Календарі",
        "Каталоги",
        "Папки",
        "Журнали",
        "Фірмові бланки",
        "Бірки та ярлики",
        "Бейджи",
        "Запрошення",
        "Листівки",
        "Сертифікати, грамоти",
        "Конверти",
        "Пластикові картки",
        "Етикетки на пляшки",
        "Постери",
        "Календарі 2026",
    ],
    "HoReCa": [
        "Меню",
        "Хенгери",
        "Костери",
        "Сети паперові",
        "Счетниці",
    ],
    "Книжкова продукція": [
        "Книги",
        "Фотокниги",
        "Кулінарні книги",
        "Методички",
    ],
    "Ексклюзивні можливості": [
        "Глянсування",
        "Цифрове тиснення",
        "Друк пантонами",
        "Друк білим кольором",
    ],
    "POS-матеріали": [
        "Хардпостери",
        "Воблери",
        "Шелфтокери",
    ],
    "Додаткові роботи": [
        "Плотерна порізка",
        "Встановлення люверсів",
    ],
}

_CATS_LIST: list[str] = list(CATEGORIES.keys())

def get_categories() -> list[str]:
    return _CATS_LIST

def get_category_name(cat_id: int) -> Optional[str]:
    if 0 <= cat_id < len(_CATS_LIST):
        return _CATS_LIST[cat_id]
    return None

def get_services(cat_id: int) -> list[str]:
    cat_name = get_category_name(cat_id)
    if cat_name is None:
        return []
    return CATEGORIES.get(cat_name, [])

def get_service_name(cat_id: int, svc_id: int) -> Optional[str]:
    services = get_services(cat_id)
    if 0 <= svc_id < len(services):
        return services[svc_id]
    return None

def is_valid_category(cat_id: int) -> bool:
    return get_category_name(cat_id) is not None

def is_valid_service(cat_id: int, svc_id: int) -> bool:
    return get_service_name(cat_id, svc_id) is not None