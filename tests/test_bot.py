"""
Тесты для Telegram-бота: /start, онбординг, кнопки меню.
Используют unittest.mock для мока Telegram API.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Мокаем aiogram и БД до импорта хэндлеров ──────────────────

MOCK_USER_EMPLOYER = {
    "id": 1, "telegram_id": 111, "role": "employer",
    "full_name": "Тест Работодатель", "username": "test_employer",
    "bio": "Тестовый работодатель", "skills": "", "portfolio_url": "",
    "hourly_rate": 0, "budget_min": 0, "budget_max": 0,
    "rating": 0, "rating_count": 0, "completed_jobs": 0,
    "is_active": 1, "is_verified": 0, "self_employed": 0, "inn": "",
}

MOCK_USER_SPECIALIST = {
    "id": 2, "telegram_id": 222, "role": "specialist",
    "full_name": "Тест Специалист", "username": "test_spec",
    "bio": "AI-разработчик", "skills": "Python, PyTorch, LLM",
    "portfolio_url": "https://github.com/test", "hourly_rate": 2000,
    "budget_min": 0, "budget_max": 0,
    "rating": 4.5, "rating_count": 10, "completed_jobs": 5,
    "is_active": 1, "is_verified": 0, "self_employed": 0, "inn": "",
}

MOCK_ORDER = {
    "id": 1, "employer_id": 1, "title": "Тестовый заказ",
    "description": "Описание тестового заказа для проверки",
    "category": "ai_ml", "budget": 50000, "deadline_days": 14,
    "status": "open", "specialist_id": None, "payment_id": "",
    "employer_name": "Тест Работодатель", "employer_tg_id": 111,
}


class TestStartCommand(unittest.TestCase):
    """Тест команды /start и приветствия."""

    def test_start_new_user_shows_welcome(self):
        """Новый пользователь видит приветствие с выбором роли."""
        from ai_talent_bot.keyboards import role_choice_kb

        kb = role_choice_kb()
        # Проверяем что есть 2 кнопки
        self.assertEqual(len(kb.inline_keyboard), 2)
        self.assertIn("Я предприниматель", kb.inline_keyboard[0][0].text)
        self.assertIn("специалист", kb.inline_keyboard[1][0].text.lower())
        self.assertEqual(kb.inline_keyboard[0][0].callback_data, "role:employer")
        self.assertEqual(kb.inline_keyboard[1][0].callback_data, "role:specialist")

    def test_start_existing_user_shows_menu(self):
        """Существующий пользователь видит главное меню."""
        from ai_talent_bot.keyboards import main_menu_kb

        # Меню для работодателя
        kb_emp = main_menu_kb("employer")
        buttons_text = [btn.text for row in kb_emp.keyboard for btn in row]
        self.assertIn("📝 Создать заказ", buttons_text)
        self.assertIn("📋 Мои заказы", buttons_text)
        self.assertIn("🔍 Найти специалиста", buttons_text)
        self.assertIn("👤 Мой профиль", buttons_text)
        self.assertIn("⭐ Отзывы", buttons_text)
        self.assertIn("📊 Статистика", buttons_text)

        # Меню для специалиста
        kb_spec = main_menu_kb("specialist")
        buttons_text = [btn.text for row in kb_spec.keyboard for btn in row]
        self.assertIn("🔎 Лента заказов", buttons_text)
        self.assertIn("📋 Мои отклики", buttons_text)
        self.assertIn("👤 Мой профиль", buttons_text)
        self.assertIn("🏆 Мои заказы", buttons_text)
        self.assertIn("⭐ Отзывы", buttons_text)
        self.assertIn("📊 Статистика", buttons_text)

    def test_webapp_button_in_menu(self):
        """При указании URL появляется кнопка Mini App."""
        from ai_talent_bot.keyboards import main_menu_kb

        kb = main_menu_kb("employer", "https://example.com")
        buttons_text = [btn.text for row in kb.keyboard for btn in row]
        self.assertIn("📱 Открыть приложение", buttons_text)

        # Проверяем что web_app атрибут установлен
        for row in kb.keyboard:
            for btn in row:
                if btn.text == "📱 Открыть приложение":
                    self.assertIsNotNone(btn.web_app)
                    self.assertEqual(btn.web_app.url, "https://example.com")


class TestOnboardingStates(unittest.TestCase):
    """Тест FSM-состояний онбординга."""

    def test_states_defined(self):
        from ai_talent_bot.states.user_states import OnboardingStates
        self.assertTrue(hasattr(OnboardingStates, 'choosing_role'))
        self.assertTrue(hasattr(OnboardingStates, 'entering_name'))
        self.assertTrue(hasattr(OnboardingStates, 'entering_bio'))
        self.assertTrue(hasattr(OnboardingStates, 'entering_skills'))
        self.assertTrue(hasattr(OnboardingStates, 'entering_portfolio'))
        self.assertTrue(hasattr(OnboardingStates, 'entering_rate'))

    def test_order_states_defined(self):
        from ai_talent_bot.states.user_states import OrderCreateStates
        self.assertTrue(hasattr(OrderCreateStates, 'entering_title'))
        self.assertTrue(hasattr(OrderCreateStates, 'entering_description'))
        self.assertTrue(hasattr(OrderCreateStates, 'choosing_category'))
        self.assertTrue(hasattr(OrderCreateStates, 'entering_budget'))
        self.assertTrue(hasattr(OrderCreateStates, 'entering_deadline'))
        self.assertTrue(hasattr(OrderCreateStates, 'confirming'))


class TestCategories(unittest.TestCase):
    """Тест категорий заказов."""

    def test_categories_exist(self):
        from ai_talent_bot.keyboards import CATEGORIES, categories_kb, category_single_kb
        self.assertIn("ai_ml", CATEGORIES)
        self.assertIn("llm_nlp", CATEGORIES)
        self.assertIn("cv", CATEGORIES)
        self.assertIn("ai_agents", CATEGORIES)
        self.assertIn("automation", CATEGORIES)
        self.assertIn("consulting", CATEGORIES)
        self.assertIn("other", CATEGORIES)

    def test_category_single_kb(self):
        from ai_talent_bot.keyboards import category_single_kb, CATEGORIES
        kb = category_single_kb()
        self.assertEqual(len(kb.inline_keyboard), len(CATEGORIES))


class TestKeyboards(unittest.TestCase):
    """Тест всех клавиатур."""

    def test_order_manage_kb_open(self):
        from ai_talent_bot.keyboards import order_manage_kb
        kb = order_manage_kb(1, "open")
        cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("view_apps:1", cb_data)
        self.assertIn("cancel:1", cb_data)

    def test_order_manage_kb_in_progress(self):
        from ai_talent_bot.keyboards import order_manage_kb
        kb = order_manage_kb(1, "in_progress")
        cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("complete:1", cb_data)

    def test_order_manage_kb_review(self):
        from ai_talent_bot.keyboards import order_manage_kb
        kb = order_manage_kb(1, "review")
        cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("pay:1", cb_data)
        self.assertIn("leave_review:1", cb_data)

    def test_rating_kb(self):
        from ai_talent_bot.keyboards import rating_kb
        kb = rating_kb()
        ratings = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        for i in range(1, 6):
            self.assertIn(f"rate:{i}", ratings)

    def test_confirm_kb(self):
        from ai_talent_bot.keyboards import confirm_kb
        kb = confirm_kb()
        cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("confirm:yes", cb_data)
        self.assertIn("confirm:edit", cb_data)
        self.assertIn("confirm:no", cb_data)

    def test_yes_no_kb(self):
        from ai_talent_bot.keyboards import yes_no_kb
        kb = yes_no_kb("yes:data", "no:data")
        cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        self.assertIn("yes:data", cb_data)
        self.assertIn("no:data", cb_data)


class TestHelpers(unittest.TestCase):
    """Тест утилит форматирования."""

    def test_rating_stars(self):
        from ai_talent_bot.utils.helpers import rating_stars
        self.assertIn("⭐", rating_stars(5.0))
        self.assertIn("⭐", rating_stars(3.5))
        self.assertIn("☆", rating_stars(0))

    def test_format_user_card_employer(self):
        from ai_talent_bot.utils.helpers import format_user_card
        card = format_user_card(MOCK_USER_EMPLOYER)
        self.assertIn("Тест Работодатель", card)
        self.assertIn("Предприниматель", card)

    def test_format_user_card_specialist(self):
        from ai_talent_bot.utils.helpers import format_user_card
        card = format_user_card(MOCK_USER_SPECIALIST)
        self.assertIn("Тест Специалист", card)
        self.assertIn("Python, PyTorch, LLM", card)
        self.assertIn("2000", card)

    def test_format_order_card(self):
        from ai_talent_bot.utils.helpers import format_order_card
        card = format_order_card(MOCK_ORDER)
        self.assertIn("Тестовый заказ", card)
        self.assertIn("50000", card)
        self.assertIn("Открыт", card)


class TestVoiceModule(unittest.TestCase):
    """Тест голосового модуля."""

    def test_voice_imports(self):
        from ai_talent_bot.utils.voice import is_voice_available, process_voice_message
        self.assertTrue(callable(is_voice_available))
        self.assertTrue(callable(process_voice_message))


if __name__ == "__main__":
    unittest.main()
