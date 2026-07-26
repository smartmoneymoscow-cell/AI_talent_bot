"""Клавиатуры бота."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

# ── Главное меню ──────────────────────────────────────────────
def main_menu_kb(role: str, webapp_url: str = "") -> ReplyKeyboardMarkup:
    webapp_btn = []
    if webapp_url:
        webapp_btn = [KeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url=webapp_url))]

    if role == "employer":
        buttons = [
            webapp_btn if webapp_btn else [KeyboardButton(text="📝 Создать заказ"), KeyboardButton(text="📋 Мои заказы")],
            [KeyboardButton(text="🔍 Найти специалиста"), KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="📊 Статистика")],
        ]
    else:
        buttons = [
            webapp_btn if webapp_btn else [KeyboardButton(text="🔎 Лента заказов"), KeyboardButton(text="📋 Мои отклики")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🏆 Мои заказы")],
            [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="📊 Статистика")],
        ]
    # Фильтруем пустые строки
    buttons = [row for row in buttons if row]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


# ── Онбординг: выбор роли ─────────────────────────────────────
def role_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Я предприниматель", callback_data="role:employer")],
        [InlineKeyboardButton(text="🧠 Я специалист по ИИ", callback_data="role:specialist")],
    ])


# ── Категории ─────────────────────────────────────────────────
CATEGORIES = {
    "ai_ml":        "🤖 ML / Data Science",
    "llm_nlp":      "💬 LLM / NLP",
    "cv":           "👁️ Computer Vision",
    "ai_agents":    "🤖 AI-агенты",
    "automation":   "⚙️ Автоматизация с ИИ",
    "consulting":   "📊 ИИ-консалтинг",
    "other":        "🔧 Другое",
}


def categories_kb(selected: set[str] | None = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    rows = []
    for key, label in CATEGORIES.items():
        prefix = "✅ " if key in selected else ""
        rows.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"cat:{key}")])
    rows.append([InlineKeyboardButton(text="✔️ Готово", callback_data="cat:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_single_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"cat_single:{key}")]
        for key, label in CATEGORIES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Заказ ─────────────────────────────────────────────────────
def order_actions_kb(order_id: int, role: str) -> InlineKeyboardMarkup:
    rows = []
    if role == "specialist":
        rows.append([InlineKeyboardButton(text="📩 Откликнуться", callback_data=f"apply:{order_id}")])
    rows.append([InlineKeyboardButton(text="📄 Подробнее", callback_data=f"order_detail:{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_manage_kb(order_id: int, status: str = "open") -> InlineKeyboardMarkup:
    rows = []
    if status == "open":
        rows.append([InlineKeyboardButton(text="👥 Отклики", callback_data=f"view_apps:{order_id}")])
        rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{order_id}")])
    elif status == "in_progress":
        rows.append([InlineKeyboardButton(text="✅ Завершить (на проверку)", callback_data=f"complete:{order_id}")])
    elif status == "review":
        rows.append([InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay:{order_id}")])
        rows.append([InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"leave_review:{order_id}")])
    elif status == "completed":
        rows.append([InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"leave_review:{order_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="my_orders:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def application_card_kb(app_id: int, order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_app:{app_id}:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_app:{app_id}:{order_id}"),
        ],
    ])


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm:edit"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
        ],
    ])


# ── Платёж ────────────────────────────────────────────────────
def payment_kb(payment_url: str, order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_pay:{order_id}")],
    ])


# ── Рейтинг ──────────────────────────────────────────────────
def rating_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"rate:{i}")
            for i in range(1, 6)
        ],
    ])


# ── Пагинация ─────────────────────────────────────────────────
def pagination_kb(prefix: str, page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}", callback_data="noop"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{page + 1}"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Подтверждение ─────────────────────────────────────────────
def yes_no_kb(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
        ],
    ])
