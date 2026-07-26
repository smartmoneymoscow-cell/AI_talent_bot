"""Обработчики оплаты."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import payment_kb, main_menu_kb
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.utils.payments import (
    calculate_fee,
    check_payment_status,
    create_payment,
    init_yookassa,
)

router = Router()


# ── Инициализация оплаты (работодатель) ───────────────────────

@router.callback_query(F.data.startswith("pay:"))
async def start_payment(callback: CallbackQuery):
    """Начать процесс оплаты за заказ."""
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order_by_id(order_id)

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    if order["status"] != "review":
        await callback.answer("Заказ не на этапе оплаты", show_alert=True)
        return

    amount = order["budget"] if order.get("budget") else 0
    if not amount:
        await callback.message.edit_text(
            "💰 Укажите сумму оплаты (₽):\n"
            "Бюджет заказа не был указан, введите сумму вручную."
        )
        # TODO: FSM для ручного ввода суммы
        await callback.answer()
        return

    await _process_payment(callback, order, amount)


async def _process_payment(callback_or_message, order: dict, amount_rub: int):
    """Создать и отправить платёж."""
    platform_fee, specialist_amount = calculate_fee(amount_rub)

    # Создаём платёж в YooKassa
    result = await create_payment(
        order_id=order["id"],
        amount_rub=amount_rub,
        description=f"Оплата заказа #{order['id']}: {order['title']}",
    )

    if not result.success:
        text = f"❌ Ошибка создания платежа:\n{result.error}"
        if hasattr(callback_or_message, "message"):
            await callback_or_message.message.edit_text(text)
        else:
            await callback_or_message.answer(text)
        return

    # Сохраняем платёж в БД
    user = await db.get_user_by_tg(callback_or_message.from_user.id)
    specialist = await db.get_user_by_id(order["specialist_id"])

    await db.create_payment(
        order_id=order["id"],
        payer_id=user["id"],
        receiver_id=order["specialist_id"],
        amount=amount_rub * 100,  # в копейках
        platform_fee=platform_fee * 100,
    )

    lines = [
        f"💳 <b>Оплата заказа #{order['id']}</b>\n",
        f"📦 {order['title']}\n",
        f"💰 Сумма: {amount_rub} ₽",
        f"📊 Комиссия платформы ({5}%): {platform_fee} ₽",
        f"👤 Специалист получит: {specialist_amount} ₽\n",
        f"🧠 Исполнитель: {specialist['full_name'] if specialist else '—'}",
    ]

    text = "\n".join(lines)

    if result.confirmation_url:
        kb = payment_kb(result.confirmation_url, order["id"])
        if hasattr(callback_or_message, "message"):
            await callback_or_message.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await callback_or_message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        # Демо-режим
        text += "\n\n⚠️ <i>Демо-режим: YooKassa не настроен. Платёж зафиксирован.</i>"
        if hasattr(callback_or_message, "message"):
            await callback_or_message.message.edit_text(text, parse_mode="HTML")
        else:
            await callback_or_message.answer(text, parse_mode="HTML")
        await _finalize_payment(order)


@router.callback_query(F.data.startswith("check_pay:"))
async def check_payment(callback: CallbackQuery):
    """Проверить статус оплаты."""
    order_id = int(callback.data.split(":")[1])
    payment = await db.get_payment_by_order(order_id)

    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return

    result = await check_payment_status(payment["yookassa_id"])

    if result.status == "succeeded":
        await db.update_payment(payment["id"], status="succeeded")
        order = await db.get_order_by_id(order_id)
        await _finalize_payment(order)
        await callback.message.edit_text(
            "✅ <b>Оплата прошла успешно!</b>\n\n"
            f"📦 Заказ #{order_id} завершён.\n"
            "Специалист получил оплату.",
            parse_mode="HTML",
        )
    elif result.status == "pending":
        await callback.answer("⏳ Оплата ещё не поступила. Попробуйте позже.", show_alert=True)
    elif result.status == "canceled":
        await db.update_payment(payment["id"], status="cancelled")
        await callback.answer("❌ Платёж отменён.", show_alert=True)
    else:
        await callback.answer(f"Статус: {result.status}", show_alert=True)


async def _finalize_payment(order: dict):
    """Завершить платёж: обновить статусы, уведомить участников."""
    await db.update_order_status(order["id"], "completed")

    # Увеличиваем счётчик выполненных заказов
    if order.get("specialist_id"):
        await db.increment_completed(order["specialist_id"])

    # Уведомляем специалиста
    if order.get("specialist_id"):
        specialist = await db.get_user_by_id(order["specialist_id"])
        if specialist:
            try:
                from aiogram import Bot
                from ai_talent_bot.config import config
                bot = Bot(token=config.BOT_TOKEN)
                await bot.send_message(
                    specialist["telegram_id"],
                    f"🎉 Заказ #{order['id']} завершён!\n\n"
                    f"📦 {order['title']}\n"
                    f"✅ Оплата поступила.\n\n"
                    "Спасибо за работу! ⭐\n"
                    "Не забудьте сформировать чек в приложении «Мой налог».",
                )
                await bot.session.close()
            except Exception:
                pass


# ── Прямая оплата (из меню заказа) ────────────────────────────

@router.callback_query(F.data.startswith("direct_pay:"))
async def direct_payment(callback: CallbackQuery):
    """Прямая оплата с указанием суммы."""
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order_by_id(order_id)

    if not order or order["status"] not in ("review", "in_progress"):
        await callback.answer("Заказ не доступен для оплаты", show_alert=True)
        return

    amount = order["budget"] if order.get("budget") else 0
    if amount:
        await _process_payment(callback, order, amount)
    else:
        await callback.message.edit_text(
            "💰 Введите сумму оплаты (₽):"
        )
        # В реальном проекте — FSM для ввода суммы
    await callback.answer()
