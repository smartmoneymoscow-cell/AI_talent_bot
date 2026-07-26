"""Обработчики онбординга."""
import json
import os
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from ai_talent_bot.keyboards import role_choice_kb, main_menu_kb
from ai_talent_bot.states.user_states import OnboardingStates
from ai_talent_bot.utils import db_queries as db
from ai_talent_bot.utils.helpers import format_user_card
from ai_talent_bot.config import config

router = Router()

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
WELCOME_PHOTO = ASSETS_DIR / "welcome.jpg"


def _skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_step")],
    ])


def _skip_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_step"),
            InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_step"),
        ],
    ])


def _build_welcome_text() -> str:
    return (
        "👋 Добро пожаловать в <b>AI Talent Hub</b>!\n\n"
        "Платформа, которая соединяет <b>предпринимателей</b> и "
        "<b>специалистов по ИИ</b> для совместной работы.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏢 <b>Предприниматель:</b>\n"
        "Создавайте заказы → получайте отклики → выбирайте исполнителя → оплачивайте\n\n"
        "🧠 <b>Специалист:</b>\n"
        "Просматривайте заказы → откликайтесь → выполняйте → получайте оплату и рейтинг\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💳 Оплата через бота · Комиссия 5% · Самозанятые\n\n"
        "👇 <b>Выберите свою роль:</b>"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
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


# ── Выбор роли ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[1]
    await state.update_data(role=role)
    await state.set_state(OnboardingStates.entering_name)
    await callback.message.edit_text(
        "👤 Как вас зовут? (ФИО или имя)"
    )
    await callback.answer()


# ── Имя ────────────────────────────────────────────────────────

@router.message(OnboardingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введите имя (минимум 2 символа):")
        return
    await state.update_data(full_name=name)
    data = await state.get_data()

    await state.set_state(OnboardingStates.entering_bio)
    if data["role"] == "employer":
        await message.answer(
            "📝 Расскажите кратко о себе и вашем бизнесе:",
            reply_markup=_skip_kb(),
        )
    else:
        await message.answer(
            "🧠 Расскажите о себе:\n"
            "Опыт, специализация, достижения в ИИ...",
            reply_markup=_skip_kb(),
        )


# ── Био ────────────────────────────────────────────────────────

@router.callback_query(F.data == "skip_step", OnboardingStates.entering_bio)
async def skip_bio_btn(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _process_bio_callback(callback, state, "")


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
            "Пример: Python, PyTorch, LLM, NLP",
            reply_markup=_skip_back_kb(),
        )
    else:
        await _finish_employer(message, state, bio)


async def _process_bio_callback(callback: CallbackQuery, state: FSMContext, bio: str):
    await state.update_data(bio=bio)
    data = await state.get_data()

    if data["role"] == "specialist":
        await state.set_state(OnboardingStates.entering_skills)
        await callback.message.edit_text(
            "🛠 Укажите ваши навыки (через запятую):\n"
            "Пример: Python, PyTorch, LLM, NLP",
            reply_markup=_skip_back_kb(),
        )
    else:
        await _finish_employer_cb(callback, state, bio)


# ── Навыки ─────────────────────────────────────────────────────

@router.callback_query(F.data == "skip_step", OnboardingStates.entering_skills)
async def skip_skills_btn(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(skills="")
    await state.set_state(OnboardingStates.entering_portfolio)
    await callback.message.edit_text(
        "🔗 Ссылка на портфолио / GitHub / LinkedIn:",
        reply_markup=_skip_back_kb(),
    )


@router.callback_query(F.data == "back_step", OnboardingStates.entering_skills)
async def back_skills(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(OnboardingStates.entering_bio)
    data = await state.get_data()
    role = data.get("role", "specialist")
    text = "📝 Расскажите кратко о себе:" if role == "employer" else "🧠 Расскажите о себе:"
    await callback.message.edit_text(text, reply_markup=_skip_kb())


@router.message(OnboardingStates.entering_skills)
async def process_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text.strip())
    await state.set_state(OnboardingStates.entering_portfolio)
    await message.answer(
        "🔗 Ссылка на портфолио / GitHub / LinkedIn:",
        reply_markup=_skip_back_kb(),
    )


# ── Портфолио ──────────────────────────────────────────────────

@router.callback_query(F.data == "skip_step", OnboardingStates.entering_portfolio)
async def skip_portfolio_btn(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(portfolio_url="")
    await state.set_state(OnboardingStates.entering_rate)
    await callback.message.edit_text(
        "💰 Укажите вашу ставку (₽/час):\nНапример: 2000",
        reply_markup=_skip_back_kb(),
    )


@router.callback_query(F.data == "back_step", OnboardingStates.entering_portfolio)
async def back_portfolio(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(OnboardingStates.entering_skills)
    await callback.message.edit_text(
        "🛠 Укажите ваши навыки (через запятую):\nПример: Python, PyTorch, LLM, NLP",
        reply_markup=_skip_back_kb(),
    )


@router.message(OnboardingStates.entering_portfolio)
async def process_portfolio(message: Message, state: FSMContext):
    await state.update_data(portfolio_url=message.text.strip())
    await state.set_state(OnboardingStates.entering_rate)
    await message.answer(
        "💰 Укажите вашу ставку (₽/час):\nНапример: 2000",
        reply_markup=_skip_back_kb(),
    )


# ── Ставка ─────────────────────────────────────────────────────

@router.callback_query(F.data == "skip_step", OnboardingStates.entering_rate)
async def skip_rate_btn(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _finish_specialist_cb(callback, state, 0)


@router.callback_query(F.data == "back_step", OnboardingStates.entering_rate)
async def back_rate(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(OnboardingStates.entering_portfolio)
    await callback.message.edit_text(
        "🔗 Ссылка на портфолио / GitHub / LinkedIn:",
        reply_markup=_skip_back_kb(),
    )


@router.message(OnboardingStates.entering_rate)
async def process_rate(message: Message, state: FSMContext):
    try:
        rate = int(message.text.strip().replace(" ", "").replace("₽", ""))
        if rate < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите число (₽/час):")
        return
    await _finish_specialist(message, state, rate)


# ── Завершение регистрации ──────────────────────────────────────

async def _finish_employer(message: Message, state: FSMContext, bio: str):
    await db.create_user(
        telegram_id=message.from_user.id,
        role="employer",
        full_name=(await state.get_data())["full_name"],
        username=message.from_user.username or "",
    )
    await db.update_user(message.from_user.id, bio=bio)
    kb = main_menu_kb("employer", config.MINI_APP_URL)
    await message.answer(
        "✅ Регистрация завершена!\n\n"
        "🏢 Вы — предприниматель.\n\n"
        "Теперь вы можете создавать заказы и находить специалистов.",
        reply_markup=kb,
    )
    await state.clear()


async def _finish_employer_cb(callback: CallbackQuery, state: FSMContext, bio: str):
    await db.create_user(
        telegram_id=callback.from_user.id,
        role="employer",
        full_name=(await state.get_data())["full_name"],
        username=callback.from_user.username or "",
    )
    await db.update_user(callback.from_user.id, bio=bio)
    kb = main_menu_kb("employer", config.MINI_APP_URL)
    await callback.message.edit_text(
        "✅ Регистрация завершена!\n\n"
        "🏢 Вы — предприниматель.\n\n"
        "Теперь вы можете создавать заказы и находить специалистов.",
    )
    await callback.message.answer("Главное меню:", reply_markup=kb)
    await state.clear()


async def _finish_specialist(message: Message, state: FSMContext, rate: int):
    data = await state.get_data()
    await db.create_user(
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
        "Теперь вы можете просматривать заказы и откликаться на проекты.",
        reply_markup=kb,
    )
    await state.clear()


async def _finish_specialist_cb(callback: CallbackQuery, state: FSMContext, rate: int):
    data = await state.get_data()
    await db.create_user(
        telegram_id=callback.from_user.id,
        role="specialist",
        full_name=data["full_name"],
        username=callback.from_user.username or "",
    )
    await db.update_user(
        callback.from_user.id,
        bio=data.get("bio", ""),
        skills=data.get("skills", ""),
        portfolio_url=data.get("portfolio_url", ""),
        hourly_rate=rate,
    )
    kb = main_menu_kb("specialist", config.MINI_APP_URL)
    await callback.message.edit_text(
        "✅ Регистрация завершена!\n\n"
        "🧠 Вы — специалист по ИИ.\n\n"
        "Теперь вы можете просматривать заказы и откликаться на проекты.",
    )
    await callback.message.answer("Главное меню:", reply_markup=kb)
    await state.clear()


# ── Обработка кнопок вне состояний ─────────────────────────────

@router.callback_query(F.data == "skip_step")
async def skip_no_state(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Нечего пропускать", show_alert=True)


@router.callback_query(F.data == "back_step")
async def back_no_state(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Некуда возвращаться", show_alert=True)
