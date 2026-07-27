"""
Tests for Mini App — prevents white screen regressions.

Run:  python -m pytest tests/test_mini_app.py -v
Needs: pip install pytest httpx
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "mini_app" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
INDEX_HTML = DIST_DIR / "index.html"


# ── Helpers ─────────────────────────────────────────────────────

def get_index_html() -> str:
    """Read built index.html or skip if not built."""
    if not INDEX_HTML.exists():
        pytest.skip("dist/index.html not built — run: cd mini_app/frontend && npm run build")
    return INDEX_HTML.read_text(encoding="utf-8")


def get_js_bundle() -> str:
    """Read the main JS bundle or skip if not built."""
    assets = DIST_DIR / "assets"
    if not assets.exists():
        pytest.skip("dist/assets/ not found")
    bundles = list(assets.glob("index-*.js"))
    if not bundles:
        pytest.skip("No index-*.js bundle found in dist/assets/")
    return bundles[0].read_text(encoding="utf-8")


def get_bundle_name() -> str:
    """Return the JS bundle filename."""
    assets = DIST_DIR / "assets"
    bundles = list(assets.glob("index-*.js"))
    return bundles[0].name if bundles else ""


# ── 1. Build integrity ─────────────────────────────────────────

class TestBuildIntegrity:
    """Verify the frontend builds and dist/ exists."""

    def test_dist_directory_exists(self):
        assert DIST_DIR.exists(), "dist/ missing — run: cd mini_app/frontend && npm run build"

    def test_dist_index_html_exists(self):
        assert INDEX_HTML.exists(), "dist/index.html missing"

    def test_dist_assets_exist(self):
        assets = DIST_DIR / "assets"
        assert assets.exists(), "dist/assets/ missing"
        bundles = list(assets.glob("index-*.js"))
        assert len(bundles) >= 1, "No JS bundle in dist/assets/"

    def test_bundle_size_not_zero(self):
        bundle = get_js_bundle()
        assert len(bundle) > 1000, "JS bundle is suspiciously small (<1KB)"

    def test_bundle_no_syntax_error(self):
        """Bundle should be valid JS (no parse errors)."""
        bundle = get_js_bundle()
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as f:
            f.write(bundle)
            tmp = f.name
        try:
            result = subprocess.run(
                ['node', '-e', f"require('vm').createScript(require('fs').readFileSync('{tmp}','utf8'))"],
                capture_output=True, text=True, timeout=10,
            )
            assert result.returncode == 0, f"JS syntax error: {result.stderr}"
        finally:
            os.unlink(tmp)


# ── 2. Telegram SDK loading ────────────────────────────────────

class TestTelegramSDK:
    """Ensure Telegram SDK loads correctly (no async race condition)."""

    def test_no_async_on_telegram_sdk(self):
        """SDK must NOT have async — causes race condition with React."""
        html = get_index_html()
        # Find the telegram-web-app.js script tag
        match = re.search(
            r'<script[^>]*src=["\']https://telegram\.org/js/telegram-web-app\.js["\'][^>]*>',
            html,
        )
        assert match, "Telegram SDK script tag not found"
        tag = match.group(0)
        assert "async" not in tag, (
            f"Telegram SDK has 'async' attribute — causes white screen! Tag: {tag}"
        )

    def test_sdk_script_present(self):
        """SDK script must exist in the HTML."""
        html = get_index_html()
        assert "telegram.org/js/telegram-web-app.js" in html

    def test_preload_for_sdk(self):
        """Preload hint helps SDK load faster."""
        html = get_index_html()
        assert 'rel="preload"' in html and "telegram-web-app.js" in html, (
            "Missing <link rel='preload'> for Telegram SDK"
        )


# ── 3. No broken color parsing ─────────────────────────────────

class TestThemeColors:
    """Ensure theme colors are not double-hashed (##ffffff)."""

    def test_no_double_hash_colors_in_bundle(self):
        """Old bug: toString(16) on hex string produced ##ffffff."""
        bundle = get_js_bundle()
        double_hash = re.search(r"##[0-9a-fA-F]{6}", bundle)
        assert not double_hash, (
            f"Found double-hash color in bundle: {double_hash.group()} — "
            "themeParams colors are already hex strings, don't add #"
        )

    def test_theme_params_used(self):
        """Bundle should reference themeParams for colors."""
        bundle = get_js_bundle()
        assert "themeParams" in bundle, "themeParams not referenced in bundle"


# ── 4. Loading timeout ─────────────────────────────────────────

class TestLoadingTimeout:
    """Ensure loading state has a hard timeout (prevents infinite spinner)."""

    def test_bundle_has_timeout_value(self):
        """Bundle should contain a timeout value (4000ms = 4e3 or similar)."""
        bundle = get_js_bundle()
        # Check for timeout patterns: 4e3, 4000, setTimeout
        has_timeout = "4e3" in bundle or "setTimeout" in bundle
        assert has_timeout, "No loading timeout found in bundle"

    def test_bundle_has_promise_race(self):
        """Promise.race fallback for fetch timeout."""
        bundle = get_js_bundle()
        assert "race" in bundle.lower(), "No Promise.race found — fetch may hang forever"

    def test_bundle_clears_timeout(self):
        """Timeout should be cleared when loadUser completes."""
        bundle = get_js_bundle()
        assert "clearTimeout" in bundle, "clearTimeout not found — timeout leak possible"


# ── 5. No old broken patterns ──────────────────────────────────

class TestNoOldPatterns:
    """Ensure old broken code is not present."""

    def test_no_telegram_web_app_ready_event(self):
        """Old code listened for 'telegram-web-app-ready' event that never fires."""
        bundle = get_js_bundle()
        assert "telegram-web-app-ready" not in bundle, (
            "Old 'telegram-web-app-ready' event listener still present — remove it"
        )

    def test_bundle_references_webapp(self):
        """Bundle should use Telegram.WebApp API."""
        bundle = get_js_bundle()
        assert "WebApp" in bundle, "WebApp not referenced — app won't work in Telegram"


# ── 6. Source file consistency ──────────────────────────────────

class TestSourceFiles:
    """Verify source files have the correct patterns."""

    def test_context_has_loading_timeout(self):
        """context.jsx must have a hard timeout for loading state."""
        context = FRONTEND_DIR / "src" / "context.jsx"
        if not context.exists():
            pytest.skip("context.jsx not found")
        src = context.read_text(encoding="utf-8")
        assert "setTimeout" in src and "setLoading(false)" in src, (
            "context.jsx missing loading timeout"
        )

    def test_context_no_async_sdk_listener(self):
        """context.jsx should NOT listen for 'telegram-web-app-ready'."""
        context = FRONTEND_DIR / "src" / "context.jsx"
        if not context.exists():
            pytest.skip("context.jsx not found")
        src = context.read_text(encoding="utf-8")
        assert "telegram-web-app-ready" not in src, (
            "context.jsx still has old 'telegram-web-app-ready' listener"
        )

    def test_context_checks_tg_ready_type(self):
        """context.jsx should check typeof tg.ready before calling."""
        context = FRONTEND_DIR / "src" / "context.jsx"
        if not context.exists():
            pytest.skip("context.jsx not found")
        src = context.read_text(encoding="utf-8")
        assert "typeof" in src and "ready" in src, (
            "context.jsx should check typeof tg.ready === 'function'"
        )

    def test_app_no_double_hash_colors(self):
        """App.jsx should not produce ##ffffff colors."""
        app = FRONTEND_DIR / "src" / "App.jsx"
        if not app.exists():
            pytest.skip("App.jsx not found")
        src = app.read_text(encoding="utf-8")
        assert "toString(16)" not in src, (
            "App.jsx still has toString(16) — themeParams colors are already hex"
        )

    def test_api_has_fetch_timeout(self):
        """api.js should have a timeout for fetch calls."""
        api = FRONTEND_DIR / "src" / "api.js"
        if not api.exists():
            pytest.skip("api.js not found")
        src = api.read_text(encoding="utf-8")
        assert "AbortController" in src or "Promise.race" in src, (
            "api.js missing fetch timeout — requests may hang forever"
        )

    def test_index_html_no_async_sdk(self):
        """Source index.html should not have async on Telegram SDK."""
        index = FRONTEND_DIR / "index.html"
        if not index.exists():
            pytest.skip("index.html not found")
        src = index.read_text(encoding="utf-8")
        match = re.search(
            r'<script[^>]*src=["\']https://telegram\.org/js/telegram-web-app\.js["\'][^>]*>',
            src,
        )
        if match:
            assert "async" not in match.group(0), (
                "Source index.html has async on Telegram SDK"
            )


# ── 7. API health (integration, needs running server) ──────────

class TestAPIHealth:
    """Integration tests — need running server at localhost:8000."""

    @pytest.fixture(autouse=True)
    def _require_server(self):
        """Skip if server not running."""
        try:
            import httpx
            r = httpx.get("http://localhost:8000/health", timeout=3)
            if r.status_code != 200:
                pytest.skip("Server not running at localhost:8000")
        except Exception:
            pytest.skip("Server not running at localhost:8000")

    def test_health_endpoint(self):
        import httpx
        r = httpx.get("http://localhost:8000/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_index_served(self):
        import httpx
        r = httpx.get("http://localhost:8000/", timeout=5)
        assert r.status_code == 200
        assert "telegram-web-app.js" in r.text

    def test_js_bundle_served(self):
        import httpx
        # Get bundle name from dist
        name = get_bundle_name()
        if not name:
            pytest.skip("No bundle found")
        r = httpx.get(f"http://localhost:8000/assets/{name}", timeout=5)
        assert r.status_code == 200
        assert "javascript" in r.headers.get("content-type", "")

    def test_api_me_requires_auth(self):
        import httpx
        r = httpx.get("http://localhost:8000/api/me", timeout=5)
        assert r.status_code == 422  # missing header

    def test_api_me_rejects_invalid_initdata(self):
        import httpx
        r = httpx.get(
            "http://localhost:8000/api/me",
            headers={"X-Telegram-Init-Data": "fake=data&hash=abc"},
            timeout=5,
        )
        assert r.status_code == 401

    def test_spa_catchall(self):
        import httpx
        r = httpx.get("http://localhost:8000/some/random/path", timeout=5)
        assert r.status_code == 200
        assert "telegram-web-app.js" in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
