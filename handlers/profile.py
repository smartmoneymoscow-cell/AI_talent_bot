"""Обработчики профиля и статистики."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import main_menu_kb, rating_kb
from ai_talent_bot.states.user_states import ProfileEditStates, ReviewStates
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.utils.helpers import format_user_card, rating_stars

router = Router()


# ── Просмотр профиля ──────────────────────────────────────────

@router.message(F.text == "👤 Мой профиль")
async def view_profile(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Вы ещё не зарегистрированы. Отправьте /start")
        return
    card = format_user_card(user)
    await message.answer(card, parse_mode="HTML")


# ── Статистика ────────────────────────────────────────────────

@router.message(F.text == "📊 Статистика")
async def view_stats(message: Message):
    stats = await db.get_user_stats(message.from_user.id)
    if not stats:
        await message.answer("Нет данных.")
        return
    user = stats["user"]
    if user["role"] == "employer":
        lines = [
            "📊 <b>Ваша статистика</b>\n",
            f"📝 Всего заказов: {sum(stats['orders_by_status'].values())}",
            f"🟢 Открытых: {stats['orders_by_status'].get('open', 0)}",
            f"🟡 В работе: {stats['orders_by_status'].get('in_progress', 0)}",
            f"✅ Завершённых: {stats['orders_by_status'].get('completed', 0)}",
            f"💰 Потрачено: {stats['total_spent'] // 100} ₽",
        ]
    else:
        stars = rating_stars(user["rating"])
        lines = [
            "📊 <b>Ваша статистика</b>\n",
            f"⭐ Рейтинг: {stars} ({user['rating']}/5)",
            f"📩 Всего откликов: {stats['total_applications']}",
            f"✅ Принято: {stats['accepted_applications']}",
            f"🏆 Выполнено заказов: {user['completed_jobs']}",
            f"💰 Заработано: {stats['total_earned'] // 100} ₽",
        ]
    await message.answer("\n".join(lines), parse_mode="HTML")


# ── Редактирование профиля ────────────────────────────────────

@router.message(F.text == "✏️ Редактировать профиль")
async def edit_profile_start(message: Message, state: FSMContext):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Имя", callback_data="edit:name")],
        [InlineKeyboardButton(text="📋 О себе", callback_data="edit:bio")],
    ])
    if user["role"] == "specialist":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Имя", callback_data="edit:name")],
            [InlineKeyboardButton(text="📋 О себе", callback_data="edit:bio")],
            [InlineKeyboardButton(text="🛠 Навыки", callback_data="edit:skills")],
            [InlineKeyboardButton(text="🔗 Портфолио", callback_data="edit:portfolio")],
            [InlineKeyboardButton(text="💰 Ставка", callback_data="edit:rate")],
        ])
    await message.answer("Что хотите изменить?", reply_markup=kb)


@router.callback_query(F.data.startswith("edit:"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    prompts = {
        "name": "Введите новое имя:",
        "bio": "Введите новое описание:",
        "skills": "Введите навыки через запятую:",
        "portfolio": "Введите ссылку на портфолио:",
        "rate": "Введите ставку (₽/час):",
    }
    states_map = {
        "name": ProfileEditStates.editing_name,
        "bio": ProfileEditStates.editing_bio,
        "skills": ProfileEditStates.editing_skills,
        "portfolio": ProfileEditStates.editing_portfolio,
        "rate": ProfileEditStates.editing_rate,
    }
    await state.update_data(edit_field=field)
    await state.set_state(states_map[field])
    await callback.message.edit_text(prompts.get(field, "Введите значение:"))
    await callback.answer()


@router.message(ProfileEditStates.editing_name)
async def save_name(message: Message, state: FSMContext):
    await db.update_user(message.from_user.id, full_name=message.text.strip())
    await message.answer("✅ Имя обновлено!")
    await state.clear()


@router.message(ProfileEditStates.editing_bio)
async def save_bio(message: Message, state: FSMContext):
    await db.update_user(message.from_user.id, bio=message.text.strip())
    await message.answer("✅ Описание обновлено!")
    await state.clear()


@router.message(ProfileEditStates.editing_skills)
async def save_skills(message: Message, state: FSMContext):
    await db.update_user(message.from_user.id, skills=message.text.strip())
    await message.answer("✅ Навыки обновлены!")
    await state.clear()


@router.message(ProfileEditStates.editing_portfolio)
async def save_portfolio(message: Message, state: FSMContext):
    await db.update_user(message.from_user.id, portfolio_url=message.text.strip())
    await message.answer("✅ Портфолио обновлено!")
    await state.clear()


@router.message(ProfileEditStates.editing_rate)
async def save_rate(message: Message, state: FSMContext):
    try:
        rate = int(message.text.strip().replace(" ", "").replace("₽", ""))
        if rate < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите число:")
        return
    await db.update_user(message.from_user.id, hourly_rate=rate)
    await message.answer(f"✅ Ставка обновлена: {rate} ₽/час")
    await state.clear()


# ── Отзывы ────────────────────────────────────────────────────

@router.message(F.text == "⭐ Отзывы")
async def view_reviews(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        return
    reviews, has_next = await db.get_reviews_for_user(user["id"], page=0)
    if not reviews:
        await message.answer("Пока нет отзывов.")
        return
    lines = ["⭐ <b>Отзывы о вас:</b>\n"]
    for r in reviews:
        stars = rating_stars(r["rating"])
        lines.append(
            f"{stars} от {r['reviewer_name']}\n"
            f"📦 Заказ: {r['order_title']}\n"
            f"💬 {r['comment']}\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data.startswith("leave_review:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    """Начать процесс оставления отзыва."""
    order_id = int(callback.data.split(":")[1])
    await state.update_data(review_order_id=order_id)
    await state.set_state(ReviewStates.entering_rating)
    await callback.message.edit_text("⭐ Оцените работу от 1 до 5:", reply_markup=rating_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("rate:"), ReviewStates.entering_rating)
async def process_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(review_rating=rating)
    await state.set_state(ReviewStates.entering_comment)
    await callback.message.edit_text("💬 Напишите комментарий к отзыву (или /skip):")
    await callback.answer()


@router.message(ReviewStates.entering_comment, F.text == "/skip")
async def skip_review_comment(message: Message, state: FSMContext):
    await _submit_review(message, state, "")


@router.message(ReviewStates.entering_comment)
async def process_review_comment(message: Message, state: FSMContext):
    await _submit_review(message, state, message.text.strip())


async def _submit_review(message: Message, state: FSMContext, comment: str):
    data = await state.get_data()
    order_id = data["review_order_id"]
    rating = data["review_rating"]

    order = await db.get_order_by_id(order_id)
    if not order:
        await message.answer("Заказ не найден.")
        await state.clear()
        return

    reviewer = await db.get_user_by_tg(message.from_user.id)
    reviewee_id = order["specialist_id"] if reviewer["role"] == "employer" else order["employer_id"]

    await db.add_review(order_id, reviewer["id"], reviewee_id, rating, comment)
    await message.answer("✅ Спасибо за отзыв!")
    await state.clear()
