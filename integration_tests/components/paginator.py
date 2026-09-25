"""Компонент пагинатора таблицы (Ant Design pagination + выбор размера страницы)."""

import re

from playwright.sync_api import Locator, expect

from integration_tests.pages.section_page import SectionPage

PAGE_SIZE_LABEL = "ui-paginator div.limit span.label"
PAGE_SIZE_OPTION = "ul.limit-ul li.limit-ul__item"
PREV_BUTTON = "li.ant-pagination-prev button"
NEXT_BUTTON = "li.ant-pagination-next button"
PAGE_ITEM = "li.ant-pagination-item"
ACTIVE_PAGE_ITEM = "li.ant-pagination-item-active"


class Paginator:
    def __init__(self, section_page: SectionPage) -> None:
        self.section_page = section_page
        page = section_page.page
        self.page = page
        self.size_label = page.locator(PAGE_SIZE_LABEL).first
        self.prev_button = page.locator(PREV_BUTTON).first
        self.next_button = page.locator(NEXT_BUTTON).first
        self.page_items = page.locator(PAGE_ITEM)
        self.active_item = page.locator(ACTIVE_PAGE_ITEM).first

    # ==================== РАЗМЕР СТРАНИЦЫ ====================
    def set_page_size(self, size: int) -> None:
        self.size_label.click()
        option = self.page.locator(PAGE_SIZE_OPTION).filter(has_text=re.compile(rf"^\s*{size}\s*$")).first
        option.click()
        self.page.keyboard.press("Escape")
        expect(self.size_label).to_contain_text(str(size))
        self.section_page.wait_for_table()

    def has_next_page(self) -> bool:
        return self.next_button.is_visible() and self.next_button.is_enabled()

    # ==================== НАВИГАЦИЯ ====================
    @property
    def current_page(self) -> int:
        return int(self.active_item.get_attribute("title") or 1)

    @property
    def last_page(self) -> int:
        return int(self.page_items.last.get_attribute("title") or 1)

    def _go(self, target: Locator, expected_page: int) -> None:
        target.click()
        expect(self.active_item).to_have_attribute("title", str(expected_page))
        self.section_page.wait_for_table()

    def next(self) -> None:
        self._go(self.next_button, self.current_page + 1)

    def prev(self) -> None:
        self._go(self.prev_button, self.current_page - 1)

    def first(self) -> None:
        self._go(self.page.locator(f"{PAGE_ITEM}[title='1']").first, 1)

    def last(self) -> None:
        self._go(self.page_items.last, self.last_page)
