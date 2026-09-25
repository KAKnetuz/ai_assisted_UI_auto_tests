"""Компонент фильтра колонки: текстовый, чекбоксный и по диапазону дат."""

from playwright.sync_api import Locator, expect

from integration_tests.pages.section_page import SectionPage
from integration_tests.utils.logger import get_logger

logger = get_logger(__name__)

FILTER_ICON = "ui-filter-wrapper"
OVERLAY = ".cdk-overlay-pane, .ant-dropdown"
APPLY_BUTTON_TEXT = "Применить"
DATE_INPUTS = ".ant-picker-input input, input[placeholder='Начало'], input[placeholder='Конец']"


class TableFilter:
    def __init__(self, section_page: SectionPage) -> None:
        self.section_page = section_page
        self.page = section_page.page

    @property
    def overlay(self) -> Locator:
        return self.page.locator(OVERLAY).filter(has=self.page.get_by_role("button", name=APPLY_BUTTON_TEXT)).first

    def open(self, title: str) -> Locator:
        logger.info(f"Открытие фильтра колонки '{title}'")
        header = self.section_page.header(title)
        header.scroll_into_view_if_needed()
        header.hover()
        header.locator(FILTER_ICON).first.click()
        expect(self.overlay).to_be_visible()
        return self.overlay

    def _apply(self, overlay: Locator) -> None:
        overlay.get_by_role("button", name=APPLY_BUTTON_TEXT).click()
        expect(overlay).to_be_hidden()
        self.section_page.wait_for_table()

    def apply_text(self, title: str, value: str) -> None:
        overlay = self.open(title)
        overlay.locator("input.ant-input").first.fill(value)
        self._apply(overlay)

    def apply_checkboxes(self, title: str, options: tuple[str, ...] | list[str]) -> None:
        overlay = self.open(title)
        for option in options:
            overlay.locator(".ant-checkbox-wrapper").filter(has_text=option).first.locator("input").check()
        self._apply(overlay)

    def apply_date_range(self, title: str, start: str, end: str) -> None:
        overlay = self.open(title)
        inputs = overlay.locator(DATE_INPUTS)
        expect(inputs).to_have_count(2)
        for field, value in ((inputs.nth(0), start), (inputs.nth(1), end)):
            field.click()
            field.fill(value)
            field.press("Enter")
        # Закрываем календарь, если остался открытым, не закрывая сам фильтр
        if self.page.locator(".ant-picker-dropdown:visible").count():
            self.page.keyboard.press("Escape")
        self._apply(overlay)
