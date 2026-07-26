"""Утилиты для работы с рейтингом."""


def calculate_new_rating(current_avg: float, count: int, new_score: int) -> tuple[float, int]:
    """Пересчёт среднего рейтинга."""
    total = current_avg * count + new_score
    new_count = count + 1
    return round(total / new_count, 2), new_count


def rating_stars(rating: float) -> str:
    """Визуализация рейтинга звёздами."""
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    empty = 5 - full - half
    return "⭐" * full + ("✨" if half else "") + "☆" * empty


def format_user_card(user: dict) -> str:
    """Карточка пользователя."""
    role_emoji = "🏢" if user["role"] == "employer" else "🧠"
    role_name = "Предприниматель" if user["role"] == "employer" else "Специалист"
    stars = rating_stars(user["rating"])

    lines = [
        f"{role_emoji} <b>{user['full_name']}</b>",
        f"📋 Роль: {role_name}",
    ]

    if user.get("bio"):
        lines.append(f"📝 {user['bio']}")

    if user["role"] == "specialist":
        if user.get("skills"):
            lines.append(f"🛠 Навыки: {user['skills']}")
        if user.get("hourly_rate"):
            lines.append(f"💰 Ставка: {user['hourly_rate']} ₽/час")
        if user.get("portfolio_url"):
            lines.append(f"🔗 Портфолио: {user['portfolio_url']}")

    lines.extend([
        f"⭐ Рейтинг: {stars} ({user['rating']}/5, {user['rating_count']} оценок)",
        f"✅ Выполнено заказов: {user['completed_jobs']}",
    ])

    if user.get("self_employed"):
        lines.append("✅ Самозанятый (верифицирован)")

    return "\n".join(lines)


def format_order_card(order: dict) -> str:
    """Карточка заказа."""
    from ai_talent_bot.keyboards import CATEGORIES
    cat_label = CATEGORIES.get(order.get("category", ""), "🔧 Другое")
    status_map = {
        "open": "🟢 Открыт",
        "in_progress": "🟡 В работе",
        "review": "🔵 На проверке",
        "completed": "✅ Завершён",
        "cancelled": "❌ Отменён",
    }
    status = status_map.get(order["status"], order["status"])

    lines = [
        f"📌 <b>{order['title']}</b>",
        f"📂 {cat_label}",
        f"📊 Статус: {status}",
    ]
    if order.get("budget"):
        lines.append(f"💰 Бюджет: {order['budget']} ₽")
    if order.get("deadline_days"):
        lines.append(f"⏰ Срок: {order['deadline_days']} дн.")
    lines.append(f"\n{order['description']}")
    return "\n".join(lines)
