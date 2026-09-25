"""Базовый Page Object: доступ к странице, настройкам и ожиданию загрузки данных."""

from playwright.sync_api import Page, expect

from integration_tests.config.constants import SPINNER
from integration_tests.config.settings import settings


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.settings = settings

    def wait_for_loading_finished(self) -> None:
        """Ждёт, пока пропадут все спиннеры загрузки (auto-wait вместо networkidle и sleep)."""
        expect(self.page.locator(SPINNER)).to_have_count(0)
