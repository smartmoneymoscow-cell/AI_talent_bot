"""Обработчики онбординга."""
import json

import os
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import role_choice_kb, main_menu_kb
from ai_talent_bot.states.user_states import OnboardingStates
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.utils.helpers import format_user_card
from ai_talent_bot.config import config

router = Router()

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
WELCOME_PHOTO = ASSETS_DIR / "welcome.jpg"


def _build_welcome_text() -> str:
    return (
        "👋 Добро пожаловать в <b>AI Talent Hub</b>!\n\n"
        "Платформа, которая соединяет <b>предпринимателей</b> и "
        "<b>специалистов по ИИ</b> для совместной работы над проектами.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏢 <b>Если вы предприниматель:</b>\n\n"
        "1️⃣ Зарегистрируйтесь как «Предприниматель»\n"
        "2️⃣ Создайте заказ — опишите задачу, укажите бюджет и срок\n"
        "3️⃣ Получайте отклики от специалистов\n"
        "4️⃣ Выберите исполнителя из списка откликов\n"
        "5️⃣ Примите работу и оплатите через бота\n"
        "6️⃣ Оставьте отзыв — это повышает рейтинг специалиста\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🧠 <b>Если вы специалист по ИИ:</b>\n\n"
        "1️⃣ Зарегистрируйтесь как «Специалист»\n"
        "2️⃣ Заполните профиль — навыки, портфолио, ставка\n"
        "3️⃣ Просматривайте ленту заказов с фильтрами\n"
        "4️⃣ Откликайтесь на подходящие проекты\n"
        "5️⃣ Выполните работу и получите оплату\n"
        "6️⃣ Получите отзыв — растите рейтинг, берите больше заказов\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💳 <b>Оплата:</b> через бота, безопасно. Комиссия платформы — 5%.\n"
        "⭐ <b>Рейтинг:</b> растёт с каждым выполненным заказом и отзывом.\n"
        "✅ <b>Самозанятые:</b> поддержка оплаты с автоматическими чеками.\n\n"
        "👇 <b>Выберите свою роль, чтобы начать:</b>"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user_by_tg(message.from_user.id)
    if user:
        kb = main_menu_kb(user["role"], config.MINI_APP_URL)
        role = "предприниматель" if user["role"] == "employer" else "специалист"
        await message.answer(
            f"С возвращением, {user['full_name']}! 👋\n"
            f"Вы зарегистрированы как {role}.",
            reply_markup=kb,
        )
        return

    welcome_text = _build_welcome_text()

    if WELCOME_PHOTO.exists():
        photo = FSInputFile(str(WELCOME_PHOTO))
        await message.answer_photo(photo=photo, caption="👋 Добро пожаловать в <b>AI Talent Hub</b>!")
        await message.answer(welcome_text, reply_markup=role_choice_kb())
    else:
        await message.answer(welcome_text, reply_markup=role_choice_kb())


@router.callback_query(F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[1]
    await state.update_data(role=role)
    await state.set_state(OnboardingStates.entering_name)
    await callback.message.edit_text(
        "Отлично! 😊\n\nКак вас зовут? (ФИО или имя)"
    )
    await callback.answer()


@router.message(OnboardingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введите имя (минимум 2 символа):")
        return
    await state.update_data(full_name=name)
    data = await state.get_data()

    if data["role"] == "employer":
        await state.set_state(OnboardingStates.entering_bio)
        await message.answer(
            "📝 Расскажите кратко о себе и вашем бизнесе:\n"
            "(Это поможет специалистам понять, с кем работают)\n\n"
            "Или отправьте /skip чтобы пропустить."
        )
    else:
        await state.set_state(OnboardingStates.entering_bio)
        await message.answer(
            "🧠 Расскажите о себе:\n"
            "Опыт, специализация, достижения в ИИ...\n\n"
            "Или отправьте /skip чтобы пропустить."
        )


@router.message(OnboardingStates.entering_bio, F.text == "/skip")
async def skip_bio(message: Message, state: FSMContext):
    await _process_bio(message, state, "")


@router.message(OnboardingStates.entering_bio)
async def process_bio(message: Message, state: FSMContext):
    await _process_bio(message, state, message.text.strip())


async def _process_bio(message: Message, state: FSMContext, bio: str):
    await state.update_data(bio=bio)
    data = await state.get_data()

    if data["role"] == "specialist":
        await state.set_state(OnboardingStates.entering_skills)
        await message.answer(
            "🛠 Укажите ваши навыки (через запятую):\n"
            "Пример: Python, PyTorch, LLM, Computer Vision, NLP"
        )
    else:
        # Для работодателя — сразу завершаем
        user = await db.create_user(
            telegram_id=message.from_user.id,
            role="employer",
            full_name=data["full_name"],
            username=message.from_user.username or "",
        )
        await db.update_user(message.from_user.id, bio=bio)
        kb = main_menu_kb("employer", config.MINI_APP_URL)
        await message.answer(
            "✅ Регистрация завершена!\n\n"
            "🏢 Вы — предприниматель.\n\n"
            "Теперь вы можете создавать заказы и находить талантливых "
            "специалистов по ИИ для ваших проектов.",
            reply_markup=kb,
        )
        await state.clear()


@router.message(OnboardingStates.entering_skills)
async def process_skills(message: Message, state: FSMContext):
    skills = message.text.strip()
    await state.update_data(skills=skills)
    await state.set_state(OnboardingStates.entering_portfolio)
    await message.answer(
        "🔗 Ссылка на портфолио / GitHub / LinkedIn:\n\n"
        "Или /skip чтобы пропустить."
    )


@router.message(OnboardingStates.entering_portfolio, F.text == "/skip")
async def skip_portfolio(message: Message, state: FSMContext):
    await _process_portfolio(message, state, "")


@router.message(OnboardingStates.entering_portfolio)
async def process_portfolio(message: Message, state: FSMContext):
    await _process_portfolio(message, state, message.text.strip())


async def _process_portfolio(message: Message, state: FSMContext, url: str):
    await state.update_data(portfolio_url=url)
    await state.set_state(OnboardingStates.entering_rate)
    await message.answer(
        "💰 Укажите вашу ставку (₽/час):\n"
        "Например: 2000\n\n"
        "Или /skip чтобы не указывать."
    )


@router.message(OnboardingStates.entering_rate, F.text == "/skip")
async def skip_rate(message: Message, state: FSMContext):
    await _finish_specialist_registration(message, state, 0)


@router.message(OnboardingStates.entering_rate)
async def process_rate(message: Message, state: FSMContext):
    try:
        rate = int(message.text.strip().replace(" ", "").replace("₽", ""))
        if rate < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите число (₽/час):")
        return
    await _finish_specialist_registration(message, state, rate)


async def _finish_specialist_registration(message: Message, state: FSMContext, rate: int):
    data = await state.get_data()
    user = await db.create_user(
        telegram_id=message.from_user.id,
        role="specialist",
        full_name=data["full_name"],
        username=message.from_user.username or "",
    )
    await db.update_user(
        message.from_user.id,
        bio=data.get("bio", ""),
        skills=data.get("skills", ""),
        portfolio_url=data.get("portfolio_url", ""),
        hourly_rate=rate,
    )
    kb = main_menu_kb("specialist", config.MINI_APP_URL)
    await message.answer(
        "✅ Регистрация завершена!\n\n"
        "🧠 Вы — специалист по ИИ.\n\n"
        "Теперь вы можете просматривать заказы, откликаться на проекты "
        "и повышать свой рейтинг, выполняя задачи.",
        reply_markup=kb,
    )
    await state.clear()
