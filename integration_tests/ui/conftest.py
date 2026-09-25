import os
import logging
import pytest
import uuid
from datetime import datetime
from playwright.sync_api import Browser, BrowserContext, Page
from integration_tests.ui.config import Config

LOG_FORMAT = '%(asctime)s | %(levelname)-7s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'

def setup_logger(name: str = __name__, level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(ch)
        logger.propagate = False
    return logger

logger = setup_logger("integration_tests")

from integration_tests.ui.config import Config

class SoftAssert:
    def __init__(self):
        self.errors: list[tuple[str, str]] = []
        self._logger = setup_logger("soft_assert")

    def check(self, condition: bool, message: str, location: str = "") -> bool:
        if not condition:
            self.errors.append((location, message))
            self._logger.error(f"❌ [{location}] {message}")
            return False
        self._logger.debug(f"✅ [{location}] {message}")
        return True

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def report_and_raise_if_failed(self) -> None:
        if self.errors:
            error_report = "\n".join([f"  [{loc}] {msg}" for loc, msg in self.errors])
            raise AssertionError(
                f"Тест завершён с {len(self.errors)} ошибкой(ами):\n{error_report}"
            )

@pytest.fixture
def soft_assert():
    return SoftAssert()

@pytest.fixture
def take_screenshot(page: Page):
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    def _screenshot(name: str, full_page: bool = False) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(results_dir, f"{name}_{timestamp}.png")
        try:
            page.screenshot(path=path, full_page=full_page)
            logger.info(f"📸 Скриншот: {path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сделать скриншот: {e}")
        return path
    return _screenshot

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        "viewport": {"width": Config.VIEWPORT_WIDTH, "height": Config.VIEWPORT_HEIGHT},
        "locale": Config.LOCALE,
        "timezone_id": getattr(Config, "TIMEZONE", "Europe/Moscow"),
        "ignore_https_errors": getattr(Config, "IGNORE_HTTPS_ERRORS", True),
        "base_url": Config.BASE_URL,
    }

@pytest.fixture(scope="function")
def browser_context(browser: Browser) -> BrowserContext:
    context = browser.new_context()
    context.set_default_timeout(Config.TEST_TIMEOUT)
    context.set_default_navigation_timeout(getattr(Config, "AUTH_TIMEOUT", Config.TEST_TIMEOUT))
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(browser_context: BrowserContext) -> Page:
    page = browser_context.new_page()
    page.set_default_timeout(Config.TEST_TIMEOUT)
    page.set_default_navigation_timeout(getattr(Config, "AUTH_TIMEOUT", Config.TEST_TIMEOUT))
    page.on("close", lambda: logger.debug("🔒 Страница закрыта"))
    yield page


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        log_file = "test-results/test_run.log"
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = lines[-50:] if len(lines) > 50 else lines
                print("\n" + "=" * 90)
                print(f"📋 ПОСЛЕДНИЕ 50 СТРОК ЛОГА (тест упал)")
                print("=" * 90)
                print(''.join(last_lines))
                print("=" * 90 + "\n")
        except Exception as e:
            print(f"⚠️ Не удалось прочитать лог-файл: {e}")
