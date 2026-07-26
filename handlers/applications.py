"""Обработчики откликов на заказы."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import application_card_kb, main_menu_kb
from ai_talent_bot.states.user_states import ApplicationStates
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.config import config

router = Router()


# ── Откликнуться на заказ ─────────────────────────────────────

@router.callback_query(F.data.startswith("apply:"))
async def start_apply(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    user = await db.get_user_by_tg(callback.from_user.id)

    if not user or user["role"] != "specialist":
        await callback.answer("Только специалисты могут откликаться", show_alert=True)
        return

    order = await db.get_order_by_id(order_id)
    if not order or order["status"] != "open":
        await callback.answer("Заказ уже не доступен", show_alert=True)
        return

    if await db.has_applied(order_id, user["id"]):
        await callback.answer("Вы уже откликнулись на этот заказ", show_alert=True)
        return

    await state.update_data(apply_order_id=order_id)
    await state.set_state(ApplicationStates.entering_message)
    await callback.message.edit_text(
        f"📩 <b>Отклик на заказ:</b> {order['title']}\n\n"
        "Напишите сопроводительное сообщение:\n"
        "— Почему вы подходите?\n"
        "— Ваш опыт в этой области\n"
        "— Предварительный план работы\n\n"
        "Или /skip чтобы пропустить.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ApplicationStates.entering_message, F.text == "/skip")
async def skip_apply_message(message: Message, state: FSMContext):
    await state.update_data(apply_message="")
    await state.set_state(ApplicationStates.entering_price)
    order_data = await state.get_data()
    order = await db.get_order_by_id(order_data["apply_order_id"])
    budget_hint = f" (бюджет заказа: {order['budget']} ₽)" if order.get("budget") else ""
    await message.answer(
        f"💰 Укажите вашу цену (₽){budget_hint}:\n\n"
        "Или /skip чтобы не указывать."
    )


@router.message(ApplicationStates.entering_message)
async def process_apply_message(message: Message, state: FSMContext):
    await state.update_data(apply_message=message.text.strip())
    await state.set_state(ApplicationStates.entering_price)
    order_data = await state.get_data()
    order = await db.get_order_by_id(order_data["apply_order_id"])
    budget_hint = f" (бюджет заказа: {order['budget']} ₽)" if order.get("budget") else ""
    await message.answer(
        f"💰 Укажите вашу цену (₽){budget_hint}:\n\n"
        "Или /skip чтобы не указывать."
    )


@router.message(ApplicationStates.entering_price, F.text == "/skip")
async def skip_apply_price(message: Message, state: FSMContext):
    await _submit_application(message, state, 0)


@router.message(ApplicationStates.entering_price)
async def process_apply_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip().replace(" ", "").replace("₽", ""))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите число (₽):")
        return
    await _submit_application(message, state, price)


async def _submit_application(message: Message, state: FSMContext, price: int):
    data = await state.get_data()
    order_id = data["apply_order_id"]
    user = await db.get_user_by_tg(message.from_user.id)

    app = await db.create_application(
        order_id=order_id,
        specialist_id=user["id"],
        message=data.get("apply_message", ""),
        proposed_price=price,
    )

    await message.answer(
        f"✅ Отклик отправлен!\n\n"
        f"📌 Заказ #{order_id}\n"
        f"{'💰 Ваша цена: ' + str(price) + ' ₽' if price else ''}\n\n"
        "Заказчик получит уведомление. Ожидайте ответа.",
        reply_markup=main_menu_kb("specialist", config.MINI_APP_URL),
    )
    await state.clear()

    # Уведомляем работодателя
    order = await db.get_order_by_id(order_id)
    if order:
        try:
            from aiogram import Bot
            from ai_talent_bot.config import config
            bot = Bot(token=config.BOT_TOKEN)
            await bot.send_message(
                order["employer_tg_id"],
                f"📩 Новый отклик на заказ #{order_id} «{order['title']}»\n\n"
                f"👤 От: {user['full_name']}\n"
                f"⭐ Рейтинг: {user['rating']}/5\n"
                f"{'💰 Цена: ' + str(price) + ' ₽' if price else ''}\n\n"
                f"Используйте «📋 Мои заказы» для управления.",
            )
            await bot.session.close()
        except Exception:
            pass


# ── Просмотр откликов на заказ ────────────────────────────────

@router.callback_query(F.data.startswith("view_apps:"))
async def view_applications(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    apps = await db.get_applications_for_order(order_id)

    if not apps:
        await callback.message.edit_text("📭 На этот заказ пока нет откликов.")
        await callback.answer()
        return

    from ai_talent_bot.utils.helpers import rating_stars
    lines = [f"📩 <b>Отклики на заказ #{order_id}:</b>\n"]

    for i, app in enumerate(apps, 1):
        stars = rating_stars(app["specialist_rating"])
        lines.append(
            f"{'─' * 20}\n"
            f"👤 <b>{app['specialist_name']}</b>\n"
            f"⭐ {stars} ({app['specialist_rating']}/5)\n"
            f"✅ Выполнено: {app['specialist_jobs']} заказов\n"
        )
        if app.get("proposed_price"):
            lines.append(f"💰 Цена: {app['proposed_price']} ₽")
        if app.get("message"):
            lines.append(f"💬 {app['message']}")
        lines.append("")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML")

    # Показываем кнопки для принятия/отклонения
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    for app in apps:
        if app["status"] == "pending":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"✅ Принять {app['specialist_name']}",
                    callback_data=f"accept_app:{app['id']}:{order_id}",
                )],
                [InlineKeyboardButton(
                    text=f"❌ Отклонить {app['specialist_name']}",
                    callback_data=f"reject_app:{app['id']}:{order_id}",
                )],
            ])
            await callback.message.answer(
                f"👤 {app['specialist_name']} — ", reply_markup=kb
            )

    await callback.answer()


# ── Принять отклик ────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept_app:"))
async def accept_application(callback: CallbackQuery):
    parts = callback.data.split(":")
    app_id = int(parts[1])
    order_id = int(parts[2])

    app = await db.get_application_by_id(app_id)
    order = await db.get_order_by_id(order_id)

    if not app or not order:
        await callback.answer("Ошибка", show_alert=True)
        return

    # Принимаем отклик
    await db.update_application_status(app_id, "accepted")
    await db.update_order_status(order_id, "in_progress", specialist_id=app["specialist_id"])

    # Отклоняем остальные отклики
    all_apps = await db.get_applications_for_order(order_id)
    for other in all_apps:
        if other["id"] != app_id and other["status"] == "pending":
            await db.update_application_status(other["id"], "rejected")

    await callback.message.edit_text(
        f"✅ Отклик принят!\n\n"
        f"👤 Специалист: {app['specialist_name']}\n"
        f"📦 Заказ: {order['title']}\n\n"
        "Заказ переведён в статус «В работе».\n"
        "После завершения вы сможете провести оплату."
    )
    await callback.answer()

    # Уведомляем специалиста
    try:
        from aiogram import Bot
        from ai_talent_bot.config import config
        bot = Bot(token=config.BOT_TOKEN)
        await bot.send_message(
            app["specialist_tg_id"],
            f"🎉 Ваш отклик принят!\n\n"
            f"📦 Заказ: {order['title']}\n"
            f"🏢 Заказчик: {order['employer_name']}\n\n"
            "Можете приступать к работе!",
        )
        await bot.session.close()
    except Exception:
        pass


@router.callback_query(F.data.startswith("reject_app:"))
async def reject_application(callback: CallbackQuery):
    parts = callback.data.split(":")
    app_id = int(parts[1])
    await db.update_application_status(app_id, "rejected")
    await callback.message.edit_text("❌ Отклик отклонён.")
    await callback.answer()


# ── Мои отклики (специалист) ──────────────────────────────────

@router.message(F.text == "📋 Мои отклики")
async def my_applications(message: Message):
    user = await db.get_user_by_tg(message.from_user.id)
    if not user:
        return

    apps, has_next = await db.get_applications_by_specialist(user["telegram_id"], page=0)
    if not apps:
        await message.answer("У вас пока нет откликов.")
        return

    status_map = {"pending": "⏳ Ожидает", "accepted": "✅ Принят", "rejected": "❌ Отклонён", "withdrawn": "↩️ Отозван"}
    lines = ["📋 <b>Ваши отклики:</b>\n"]
    for app in apps:
        status = status_map.get(app["status"], app["status"])
        lines.append(
            f"📌 #{app['order_id']} — {app['order_title']}\n"
            f"📊 {status}\n"
            f"{'💰 Цена: ' + str(app['proposed_price']) + ' ₽' if app.get('proposed_price') else ''}\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")
