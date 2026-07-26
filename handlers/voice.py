"""
Обработчик голосовых сообщений.
Перехватывает голос → распознаёт текст → передаёт в текущий хэндлер.
"""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message

from ai_talent_bot.utils.voice import process_voice_message, is_voice_available

router = Router(name="voice")


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    """Перехват любого голосового сообщения."""
    if not is_voice_available():
        await message.answer(
            "🎤 Голосовые пока не поддерживаются.\n"
            "Установите модель Vosk (см. README)."
        )
        return

    # Уведомляем, что распознаём
    status_msg = await message.answer("🎤 Распознаю голосовое...")

    text = await process_voice_message(bot, message.voice.file_id)

    if not text:
        await status_msg.edit_text("❌ Не удалось распознать речь. Попробуйте ещё раз или напишите текстом.")
        return

    await status_msg.edit_text(f"🎤 Распознано: <i>{text}</i>\n\n⏳ Обрабатываю...")

    # Создаём новый объект Message с текстом, чтобы передать в существующие хэндлеры
    # Используем трюк: отправляем сообщение от имени бота и сразу удаляем,
    # а вместо этого напрямую вызываем логику обработки текста
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey

    # Получаем текущее состояние
    key = StorageKey(
        bot_id=bot.id,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
    )
    storage = bot.fsm.storage
    state = FSMContext(storage=storage, key=key)
    current_state = await state.get_state()

    if not current_state:
        await status_msg.edit_text(
            f"🎤 Распознано: <i>{text}</i>\n\n"
            "Отправьте /start чтобы начать, или напишите текстом."
        )
        return

    # Имитируем текстовое сообщение — передаём в соответствующий обработчик
    # Просто подменяем message.text и вызываем нужную функцию
    message.text = text  # type: ignore[attr-defined]

    # Маршрутизация по текущему состоянию
    from ai_talent_bot.states.user_states import (
        OnboardingStates,
        OrderCreateStates,
        ApplicationStates,
        ProfileEditStates,
        SearchStates,
        ReviewStates,
    )

    handler_map = {
        # Онбординг
        OnboardingStates.entering_name.state: "onboarding.process_name",
        OnboardingStates.entering_bio.state: "onboarding.process_bio",
        OnboardingStates.entering_skills.state: "onboarding.process_skills",
        OnboardingStates.entering_portfolio.state: "onboarding.process_portfolio",
        OnboardingStates.entering_rate.state: "onboarding.process_rate",
        # Заказы
        OrderCreateStates.entering_title.state: "orders.order_title",
        OrderCreateStates.entering_description.state: "orders.order_description",
        OrderCreateStates.entering_budget.state: "orders.order_budget",
        OrderCreateStates.entering_deadline.state: "orders.order_deadline",
        # Отклики
        ApplicationStates.entering_message.state: "applications.process_apply_message",
        ApplicationStates.entering_price.state: "applications.process_apply_price",
        # Профиль
        ProfileEditStates.editing_name.state: "profile.save_name",
        ProfileEditStates.editing_bio.state: "profile.save_bio",
        ProfileEditStates.editing_skills.state: "profile.save_skills",
        ProfileEditStates.editing_portfolio.state: "profile.save_portfolio",
        ProfileEditStates.editing_rate.state: "profile.save_rate",
        # Поиск
        SearchStates.entering_query.state: "search.process_search",
        # Отзыв
        ReviewStates.entering_comment.state: "profile.process_review_comment",
    }

    handler_name = handler_map.get(current_state)

    if not handler_name:
        await status_msg.edit_text(
            f"🎤 Распознано: <i>{text}</i>\n\n"
            "В этом состоянии голосовой ввод не поддерживается. Напишите текстом."
        )
        return

    # Импортируем и вызываем нужный хэндлер
    try:
        module_name, func_name = handler_name.rsplit(".", 1)
        modules = {
            "onboarding": "ai_talent_bot.handlers.onboarding",
            "orders": "ai_talent_bot.handlers.orders",
            "applications": "ai_talent_bot.handlers.applications",
            "profile": "ai_talent_bot.handlers.profile",
            "search": "ai_talent_bot.handlers.search",
        }
        import importlib
        mod = importlib.import_module(modules[module_name])
        func = getattr(mod, func_name)

        # Удаляем статус-сообщение
        await status_msg.delete()

        # Вызываем хэндлер с нашим message (у которого text заменён)
        await func(message, state)

    except Exception as e:
        await status_msg.edit_text(
            f"🎤 Распознано: <i>{text}</i>\n\n"
            f"⚠️ Ошибка обработки: {e}\n"
            "Попробуйте написать текстом."
        )
