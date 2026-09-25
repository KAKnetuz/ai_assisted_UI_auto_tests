"""Компонент сортировки колонок: цикл ASC → DESC → сброс по клику на иконку."""

from integration_tests.config.constants import SORT_SAMPLE_SIZE
from integration_tests.helpers.parsers import parse_column
from integration_tests.pages.section_page import SectionPage

SORT_ICON = "ui-sort"


class TableSorting:
    def __init__(self, section_page: SectionPage) -> None:
        self.section_page = section_page

    def toggle(self, title: str) -> None:
        """Один клик по иконке сортировки: без сортировки → ASC → DESC → без сортировки."""
        header = self.section_page.header(title)
        header.scroll_into_view_if_needed()
        icon = header.locator(SORT_ICON).first
        # Некоторые таблицы сортируют по клику на заголовок, без отдельной иконки
        (icon if icon.count() else header).click()
        self.section_page.wait_for_table()

    def values(self, title: str) -> list:
        column = self.section_page.section.column(title)
        texts = self.section_page.column_texts(title)[:SORT_SAMPLE_SIZE]
        return parse_column(texts, column.type)
