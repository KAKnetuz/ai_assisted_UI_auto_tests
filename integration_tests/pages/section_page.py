"""
Универсальный Page Object раздела с таблицей.
Поведение задаётся описанием Section из config/sections.py.
"""

import re

from playwright.sync_api import Locator, Page, expect

from integration_tests.config.constants import EMPTY_STATE, SECTION_TAB, SIDEBAR_LINK
from integration_tests.config.sections import Column, Section
from integration_tests.pages.base_page import BasePage
from integration_tests.pages.login_page import LoginPage
from integration_tests.utils.logger import get_logger

logger = get_logger(__name__)

# Индекс колонки: сначала по CDK-классу, затем по точному тексту, затем по началу текста
# (заголовки бывают обрезаны многоточием)
_COLUMN_INDEX_JS = """
(headers, [key, title]) => {
    const texts = headers.map(th => th.innerText.replace(/\\s+/g, ' ').trim());
    if (key) {
        const byKey = headers.findIndex(th => th.classList.contains('cdk-column-' + key));
        if (byKey >= 0) return byKey;
    }
    const exact = texts.findIndex(t => t === title);
    return exact >= 0 ? exact : texts.findIndex(t => t.startsWith(title));
}
"""

_COLUMN_TEXTS_JS = """
(rows, index) => rows.map(row => {
    const cell = row.querySelectorAll('td')[index];
    return cell ? cell.innerText.trim() : null;
})
"""


class SectionPage(BasePage):
    def __init__(self, page: Page, section: Section) -> None:
        super().__init__(page)
        self.section = section
        self.table = page.locator(section.table).first
        self.rows = self.table.locator("tbody tr:visible")
        self.empty_state = self.table.locator(EMPTY_STATE)

    # ==================== НАВИГАЦИЯ ====================
    def open(self) -> "SectionPage":
        LoginPage(self.page).open_app()
        s = self.section
        logger.info(f"Переход в раздел: {s.title}")
        if s.nav_selector:
            self.page.locator(s.nav_selector).first.click()
        if s.menu:
            self.page.locator(SIDEBAR_LINK).filter(has_text=s.menu).first.click()
        if s.tab:
            self.page.locator(SECTION_TAB).filter(has_text=s.tab).first.click()
        if s.url_pattern:
            expect(self.page).to_have_url(re.compile(s.url_pattern))
        self.wait_for_table()
        return self

    def wait_for_table(self) -> None:
        expect(self.table).to_be_visible()
        self.wait_for_loading_finished()
        expect(self.rows.first.or_(self.empty_state).filter(visible=True).first).to_be_visible()

    # ==================== ЗАГОЛОВКИ ====================
    def header_by_selector(self, column: Column) -> Locator:
        return self.table.locator(column.header_selector).first

    def column_index(self, title: str) -> int:
        column = self.section.column(title)
        index = self.table.locator("thead th").evaluate_all(_COLUMN_INDEX_JS, [column.key, column.title])
        if index < 0:
            raise AssertionError(f"Колонка '{title}' не найдена в таблице раздела '{self.section.id}'")
        return index

    def header(self, title: str) -> Locator:
        return self.table.locator("thead th").nth(self.column_index(title))

    # ==================== ДАННЫЕ ====================
    def row_count(self) -> int:
        if self.empty_state.is_visible():
            return 0
        return self.rows.count()

    def column_texts(self, title: str) -> list[str | None]:
        if self.row_count() == 0:
            return []
        return self.rows.evaluate_all(_COLUMN_TEXTS_JS, self.column_index(title))

    def row_texts(self) -> list[str]:
        """Полный текст строк — используется как «отпечаток» порядка и содержимого страницы."""
        if self.row_count() == 0:
            return []
        return [text.strip() for text in self.rows.all_inner_texts()]

    def first_value(self, title: str) -> str | None:
        """Первое непустое значение колонки на текущей странице."""
        return next((t for t in self.column_texts(title) if t and t not in ("-", "—")), None)
