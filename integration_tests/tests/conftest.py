"""
Фикстуры UI-тестов.
- Контекст браузера из settings (viewport, locale, base_url и т.д.)
- Одна авторизация на сессию: состояние (cookies SSO) переиспользуется всеми тестами
- Таймауты по умолчанию для действий и expect
Скриншоты, трейсы и видео при падении пишет pytest-playwright (см. addopts в pyproject.toml).
"""

from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect

from integration_tests.config.settings import settings
from integration_tests.pages.login_page import LoginPage


def pytest_configure(config: pytest.Config) -> None:
    expect.set_options(timeout=settings.EXPECT_TIMEOUT)


@pytest.fixture(scope="session")
def auth_state(browser: Browser, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Логинится один раз за сессию и сохраняет состояние браузера."""
    context = browser.new_context(**settings.context_args)
    try:
        page = context.new_page()
        page.set_default_timeout(settings.ACTION_TIMEOUT)
        LoginPage(page).open_app()
        path = tmp_path_factory.mktemp("auth") / "state.json"
        context.storage_state(path=path)
    finally:
        context.close()
    return path


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, auth_state: Path) -> dict:
    return {**browser_context_args, **settings.context_args, "storage_state": auth_state}


@pytest.fixture(autouse=True)
def _default_timeouts(page: Page) -> None:
    page.set_default_timeout(settings.ACTION_TIMEOUT)
    page.set_default_navigation_timeout(settings.NAVIGATION_TIMEOUT)
