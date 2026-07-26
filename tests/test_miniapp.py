"""
Тесты для Mini App API (FastAPI).
"""
import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mini_app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Мокаем конфиг ─────────────────────────────────────────────

os.environ["BOT_TOKEN"] = "test_token_123"
os.environ["DB_PATH"] = ":memory:"


class TestMiniAppImports(unittest.TestCase):
    """Тест импортов Mini App."""

    def test_backend_imports(self):
        from mini_app.backend.main import app, validate_init_data
        self.assertTrue(hasattr(app, 'routes'))
        self.assertTrue(callable(validate_init_data))


class TestInitDataValidation(unittest.TestCase):
    """Тест валидации Telegram initData."""

    def test_empty_data_returns_none(self):
        from mini_app.backend.main import validate_init_data
        result = validate_init_data("", "test_token")
        self.assertIsNone(result)

    def test_invalid_data_returns_none(self):
        from mini_app.backend.main import validate_init_data
        result = validate_init_data("invalid=data", "test_token")
        self.assertIsNone(result)

    def test_no_hash_returns_none(self):
        from mini_app.backend.main import validate_init_data
        result = validate_init_data("user=%7B%22id%22%3A123%7D", "test_token")
        self.assertIsNone(result)


class TestAPIRoutes(unittest.TestCase):
    """Тест что все API маршруты зарегистрированы."""

    def test_routes_exist(self):
        from mini_app.backend.main import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]

        expected = [
            "/api/me",
            "/api/me/stats",
            "/api/orders",
            "/api/orders/{order_id}",
            "/api/orders/{order_id}/applications",
            "/api/applications",
            "/api/specialists",
            "/api/specialists/{user_id}",
            "/api/reviews",
            "/api/avatar/{telegram_id}",
        ]
        for path in expected:
            self.assertIn(path, routes, f"Route {path} not found")


class TestPydanticModels(unittest.TestCase):
    """Тест Pydantic моделей."""

    def test_user_update(self):
        from mini_app.backend.main import UserUpdate
        data = UserUpdate(bio="test bio", skills="Python")
        self.assertEqual(data.bio, "test bio")
        self.assertEqual(data.skills, "Python")
        self.assertIsNone(data.portfolio_url)

    def test_order_create(self):
        from mini_app.backend.main import OrderCreate
        data = OrderCreate(title="Test", description="Test desc", budget=50000)
        self.assertEqual(data.title, "Test")
        self.assertEqual(data.budget, 50000)

    def test_order_create_optional_budget(self):
        from mini_app.backend.main import OrderCreate
        data = OrderCreate(title="Test", description="Test desc")
        self.assertEqual(data.budget, 0)

    def test_application_create(self):
        from mini_app.backend.main import ApplicationCreate
        data = ApplicationCreate(order_id=1, message="I can do it", proposed_price=30000)
        self.assertEqual(data.order_id, 1)
        self.assertEqual(data.proposed_price, 30000)

    def test_review_create_valid_rating(self):
        from mini_app.backend.main import ReviewCreate
        data = ReviewCreate(order_id=1, rating=5, comment="Great work!")
        self.assertEqual(data.rating, 5)


class TestFrontendBuild(unittest.TestCase):
    """Тест что фронтенд собран."""

    def test_dist_exists(self):
        dist_dir = os.path.join(os.path.dirname(__file__), "..", "mini_app", "frontend", "dist")
        self.assertTrue(os.path.exists(dist_dir), "Frontend dist/ not found")

    def test_index_html_exists(self):
        index = os.path.join(os.path.dirname(__file__), "..", "mini_app", "frontend", "dist", "index.html")
        self.assertTrue(os.path.exists(index), "dist/index.html not found")


if __name__ == "__main__":
    unittest.main()
