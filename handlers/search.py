"""Обработчики поиска и ленты заказов."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import (
    CATEGORIES,
    categories_kb,
    category_single_kb,
    order_actions_kb,
    pagination_kb,
)
from ai_talent_bot.states.user_states import SearchStates
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.utils.helpers import format_order_card, format_user_card, rating_stars

router = Router()


# ── Лента заказов (для специалистов) ──────────────────────────

@router.message(F.text == "🔎 Лента заказов")
async def orders_feed(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        return
    await _show_feed(message, user, 0, "")


async def _show_feed(target, user: dict, page: int, category: str):
    orders, has_next = await db.get_open_orders(category=category, page=page)
    if not orders:
        text = "📭 Пока нет открытых заказов." if page == 0 else "Больше заказов нет."
        if hasattr(target, "message"):
            await target.message.edit_text(text)
        else:
            await target.answer(text)
        return

    lines = [f"🔎 <b>Лента заказов (стр. {page + 1}):</b>\n"]
    for o in orders:
        cat = CATEGORIES.get(o.get("category", ""), "🔧")
        lines.append(f"📌 <b>#{o['id']}</b> — {o['title']}")
        lines.append(f"   {cat}")
        if o.get("budget"):
            lines.append(f"   💰 Бюджет: {o['budget']} ₽")
        if o.get("deadline_days"):
            lines.append(f"   ⏰ Срок: {o['deadline_days']} дн.")
        lines.append(f"   🏢 {o['employer_name']}")
        lines.append("")

    text = "\n".join(lines)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for o in orders:
        rows.append([InlineKeyboardButton(
            text=f"📄 #{o['id']} — {o['title'][:30]}",
            callback_data=f"order_detail:{o['id']}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"feed:{page - 1}:{category}"))
    nav.append(InlineKeyboardButton(text="🔍 Фильтр", callback_data="feed_filter"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"feed:{page + 1}:{category}"))
    rows.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if hasattr(target, "message"):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("feed:"))
async def feed_page(callback: CallbackQuery):
    parts = callback.data.split(":")
    page = int(parts[1])
    category = parts[2] if len(parts) > 2 else ""
    user = await db.get_user_by_tg(callback.from_user.id)
    await _show_feed(callback, user, page, category)
    await callback.answer()


@router.callback_query(F.data == "feed_filter")
async def feed_filter(callback: CallbackQuery):
    await callback.message.edit_text(
        "📂 Выберите категорию для фильтрации:",
        reply_markup=category_single_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_single:"))
async def apply_filter(callback: CallbackQuery):
    category = callback.data.split(":")[1]
    user = await db.get_user_by_tg(callback.from_user.id)
    await _show_feed(callback, user, 0, category)
    await callback.answer()


# ── Детали заказа ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("order_detail:"))
async def order_detail(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    card = format_order_card(order)
    user = await db.get_user_by_tg(callback.from_user.id)
    kb = order_actions_kb(order_id, user["role"])
    await callback.message.edit_text(card, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ── Поиск специалистов (для работодателей) ────────────────────

@router.message(F.text == "🔍 Найти специалиста")
async def search_specialists(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user or user["role"] != "employer":
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск по навыкам", callback_data="search:skills")],
        [InlineKeyboardButton(text="⭐ Топ по рейтингу", callback_data="search:top")],
        [InlineKeyboardButton(text="💰 По ставке", callback_data="search:rate")],
    ])
    await message.answer("🔍 Как ищем специалиста?", reply_markup=kb)


@router.callback_query(F.data.startswith("search:"))
async def search_type(callback: CallbackQuery, state: FSMContext):
    search_type = callback.data.split(":")[1]

    if search_type == "top":
        specialists, _ = await db.search_specialists(page=0)
        await _show_specialists_list(callback, specialists, 0, has_next=False)
    elif search_type == "skills":
        await state.set_state(SearchStates.entering_query)
        await callback.message.edit_text("🔍 Введите навык для поиска:\nНапример: Python, PyTorch, NLP")
    elif search_type == "rate":
        await state.update_data(search_mode="rate")
        await state.set_state(SearchStates.entering_query)
        await callback.message.edit_text("💰 Максимальная ставка (₽/час):\nНапример: 3000")
    await callback.answer()


@router.message(SearchStates.entering_query)
async def process_search(message: Message, state: FSMContext):
    data = await state.get_data()
    query = message.text.strip()

    if data.get("search_mode") == "rate":
        try:
            max_rate = int(query.replace(" ", "").replace("₽", ""))
        except ValueError:
            await message.answer("Введите число:")
            return
        specialists, has_next = await db.search_specialists(max_rate=max_rate, page=0)
    else:
        specialists, has_next = await db.search_specialists(query=query, page=0)

    await state.clear()
    await _show_specialists_list_msg(message, specialists, 0, has_next)


async def _show_specialists_list(callback: CallbackQuery, specialists: list, page: int, has_next: bool):
    if not specialists:
        await callback.message.edit_text("😕 Специалисты не найдены.")
        return

    lines = [f"🔍 <b>Специалисты (стр. {page + 1}):</b>\n"]
    for s in specialists:
        stars = rating_stars(s["rating"])
        lines.append(
            f"🧠 <b>{s['full_name']}</b>\n"
            f"⭐ {stars} ({s['rating']}/5) | ✅ {s['completed_jobs']} заказов\n"
            f"🛠 {s.get('skills', 'не указаны')}\n"
            f"💰 {s.get('hourly_rate', 0)} ₽/час\n"
        )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for s in specialists:
        rows.append([InlineKeyboardButton(
            text=f"👤 {s['full_name']}",
            callback_data=f"view_spec:{s['id']}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"spec_list:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"spec_list:{page + 1}"))
    if nav:
        rows.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)


async def _show_specialists_list_msg(message: Message, specialists: list, page: int, has_next: bool):
    if not specialists:
        await message.answer("😕 Специалисты не найдены.")
        return

    lines = [f"🔍 <b>Специалисты (стр. {page + 1}):</b>\n"]
    for s in specialists:
        stars = rating_stars(s["rating"])
        lines.append(
            f"🧠 <b>{s['full_name']}</b>\n"
            f"⭐ {stars} ({s['rating']}/5) | ✅ {s['completed_jobs']} заказов\n"
            f"🛠 {s.get('skills', 'не указаны')}\n"
            f"💰 {s.get('hourly_rate', 0)} ₽/час\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data.startswith("view_spec:"))
async def view_specialist(callback: CallbackQuery):
    spec_id = int(callback.data.split(":")[1])
    spec = await db.get_user_by_id(spec_id)
    if not spec:
        await callback.answer("Не найден", show_alert=True)
        return
    card = format_user_card(spec)
    await callback.message.edit_text(card, parse_mode="HTML")
    await callback.answer()
