"""Обработчики заказов."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import (
    CATEGORIES,
    category_single_kb,
    confirm_kb,
    main_menu_kb,
    order_manage_kb,
    pagination_kb,
)
from ai_talent_bot.states.user_states import OrderCreateStates
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.utils.helpers import format_order_card

router = Router()


# ── Создание заказа ───────────────────────────────────────────

@router.message(F.text == "📝 Создать заказ")
async def create_order_start(message: Message, state: FSMContext):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user or user["role"] != "employer":
        await message.answer("Только предприниматели могут создавать заказы.")
        return
    await state.set_state(OrderCreateStates.entering_title)
    await message.answer(
        "📌 <b>Создание заказа</b>\n\n"
        "Шаг 1/5: Введите название проекта:",
        parse_mode="HTML",
    )


@router.message(OrderCreateStates.entering_title)
async def order_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if len(title) < 5:
        await message.answer("Название слишком короткое (минимум 5 символов):")
        return
    await state.update_data(title=title)
    await state.set_state(OrderCreateStates.entering_description)
    await message.answer(
        "📝 Шаг 2/5: Опишите задачу подробно:\n"
        "— Что нужно сделать?\n"
        "— Какие технологии желательны?\n"
        "— Какой ожидаемый результат?"
    )


@router.message(OrderCreateStates.entering_description)
async def order_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if len(desc) < 20:
        await message.answer("Описание слишком короткое. Опишите задачу подробнее:")
        return
    await state.update_data(description=desc)
    await state.set_state(OrderCreateStates.choosing_category)
    await message.answer(
        "📂 Шаг 3/5: Выберите категорию:",
        reply_markup=category_single_kb(),
    )


@router.callback_query(F.data.startswith("cat_single:"), OrderCreateStates.choosing_category)
async def order_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(OrderCreateStates.entering_budget)
    await callback.message.edit_text(
        "💰 Шаг 4/5: Укажите бюджет (₽):\n"
        "Например: 50000\n\n"
        "Или /skip если не определён."
    )
    await callback.answer()


@router.message(OrderCreateStates.entering_budget, F.text == "/skip")
async def skip_budget(message: Message, state: FSMContext):
    await state.update_data(budget=0)
    await state.set_state(OrderCreateStates.entering_deadline)
    await message.answer(
        "⏰ Шаг 5/5: Срок выполнения (в днях):\n"
        "Например: 14\n\n"
        "Или /skip если не определён."
    )


@router.message(OrderCreateStates.entering_budget)
async def order_budget(message: Message, state: FSMContext):
    try:
        budget = int(message.text.strip().replace(" ", "").replace("₽", ""))
        if budget < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите число (₽):")
        return
    await state.update_data(budget=budget)
    await state.set_state(OrderCreateStates.entering_deadline)
    await message.answer(
        "⏰ Шаг 5/5: Срок выполнения (в днях):\n"
        "Например: 14\n\n"
        "Или /skip если не определён."
    )


@router.message(OrderCreateStates.entering_deadline, F.text == "/skip")
async def skip_deadline(message: Message, state: FSMContext):
    await state.update_data(deadline_days=0)
    await _show_order_preview(message, state)


@router.message(OrderCreateStates.entering_deadline)
async def order_deadline(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.answer("Введите число дней:")
        return
    await state.update_data(deadline_days=days)
    await _show_order_preview(message, state)


async def _show_order_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(OrderCreateStates.confirming)

    cat_label = CATEGORIES.get(data.get("category", ""), "🔧 Другое")
    lines = [
        "📋 <b>Предпросмотр заказа:</b>\n",
        f"📌 <b>{data['title']}</b>",
        f"📂 {cat_label}",
    ]
    if data.get("budget"):
        lines.append(f"💰 Бюджет: {data['budget']} ₽")
    if data.get("deadline_days"):
        lines.append(f"⏰ Срок: {data['deadline_days']} дн.")
    lines.append(f"\n{data['description']}")
    lines.append("\nВсё верно?")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=confirm_kb())


@router.callback_query(F.data == "confirm:yes", OrderCreateStates.confirming)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await db.get_user_by_tg(callback.from_user.id)

    order = await db.create_order(
        employer_id=user["id"],
        title=data["title"],
        description=data["description"],
        category=data.get("category", "ai_general"),
        budget=data.get("budget", 0),
        deadline_days=data.get("deadline_days", 0),
    )

    await callback.message.edit_text(
        f"✅ Заказ #{order['id']} создан!\n\n"
        f"📌 {order['title']}\n\n"
        "Специалисты увидят его в ленте заказов.",
    )
    await state.clear()


@router.callback_query(F.data == "confirm:edit", OrderCreateStates.confirming)
async def edit_order(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreateStates.entering_title)
    await callback.message.edit_text("📌 Введите новое название проекта:")
    await callback.answer()


@router.callback_query(F.data == "confirm:no", OrderCreateStates.confirming)
async def cancel_order_creation(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Создание заказа отменено.")
    await state.clear()


# ── Мои заказы (работодатель) ────────────────────────────────

@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        return
    await _show_orders_page(message, user, 0)


async def _show_orders_page(message_or_callback, user: dict, page: int):
    orders, has_next = await db.get_orders_by_employer(user["telegram_id"], page=page)
    if not orders:
        text = "У вас пока нет заказов." if page == 0 else "Больше заказов нет."
        if hasattr(message_or_callback, "message"):
            await message_or_callback.message.edit_text(text)
        else:
            await message_or_callback.answer(text)
        return

    lines = [f"📋 <b>Ваши заказы (стр. {page + 1}):</b>\n"]
    for o in orders:
        status_emoji = {"open": "🟢", "in_progress": "🟡", "review": "🔵", "completed": "✅", "cancelled": "❌"}
        emoji = status_emoji.get(o["status"], "⚪")
        lines.append(f"{emoji} #{o['id']} — {o['title']}")
        if o.get("budget"):
            lines.append(f"   💰 {o['budget']} ₽")
        lines.append("")

    text = "\n".join(lines)

    # Inline-кнопки для управления каждым заказом
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for o in orders:
        rows.append([InlineKeyboardButton(
            text=f"⚙️ #{o['id']} — {o['title'][:30]}",
            callback_data=f"manage_order:{o['id']}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"my_orders:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"my_orders:{page + 1}"))
    if nav:
        rows.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if hasattr(message_or_callback, "message"):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("my_orders:"))
async def my_orders_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    user = await db.get_user_by_tg(callback.from_user.id)
    await _show_orders_page(callback, user, page)
    await callback.answer()


@router.callback_query(F.data.startswith("manage_order:"))
async def manage_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    card = format_order_card(order)
    apps = await db.get_applications_for_order(order_id)
    card += f"\n\n📩 Откликов: {len(apps)}"
    await callback.message.edit_text(card, parse_mode="HTML", reply_markup=order_manage_kb(order_id, order['status']))
    await callback.answer()


# ── Мои заказы (специалист) ──────────────────────────────────

@router.message(F.text == "🏆 Мои заказы")
async def specialist_orders(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user or user["role"] != "specialist":
        return
    orders, has_next = await db.get_orders_by_specialist(user["telegram_id"], page=0)
    if not orders:
        await message.answer("У вас пока нет заказов в работе.")
        return

    lines = ["🏆 <b>Ваши заказы:</b>\n"]
    for o in orders:
        lines.append(f"📌 #{o['id']} — {o['title']}")
        lines.append(f"📊 Статус: {o['status']}")
        lines.append("")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ── Отмена заказа ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel:"))
async def cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order_by_id(order_id)
    if not order or order["employer_id"] != (await db.get_user_by_tg(callback.from_user.id))["id"]:
        await callback.answer("Нет доступа", show_alert=True)
        return
    if order["status"] not in ("open",):
        await callback.answer("Нельзя отменить заказ в этом статусе", show_alert=True)
        return
    await db.update_order_status(order_id, "cancelled")
    await callback.message.edit_text("❌ Заказ отменён.")
    await callback.answer()


# ── Завершение заказа ─────────────────────────────────────────

@router.callback_query(F.data.startswith("complete:"))
async def complete_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order_by_id(order_id)
    if not order or order["status"] != "in_progress":
        await callback.answer("Нельзя завершить", show_alert=True)
        return

    await db.update_order_status(order_id, "review")
    await callback.message.edit_text(
        "🔵 Заказ переведён на проверку.\n\n"
        "После подтверждения оплаты специалист получит деньги."
    )

    # Уведомляем специалиста
    if order.get("specialist_id"):
        spec = await db.get_user_by_id(order["specialist_id"])
        if spec:
            try:
                from aiogram import Bot
                from ai_talent_bot.config import config
                bot = Bot(token=config.BOT_TOKEN)
                await bot.send_message(
                    spec["telegram_id"],
                    f"📦 Заказ #{order_id} «{order['title']}» переведён на проверку.\n"
                    "Ожидает подтверждения оплаты от заказчика.",
                )
                await bot.session.close()
            except Exception:
                pass

    await callback.answer()
