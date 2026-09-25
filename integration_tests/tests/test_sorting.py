"""Сортировка колонок: полный цикл ASC → DESC → сброс к исходному порядку."""

import pytest
from playwright.sync_api import Page

from integration_tests.components.table_sorting import TableSorting
from integration_tests.config.sections import SECTIONS, Section
from integration_tests.helpers.parsers import is_sorted
from integration_tests.pages.section_page import SectionPage

pytestmark = [pytest.mark.ui, pytest.mark.sorting]

SORT_CASES = [
    pytest.param(section, title, id=f"{section.id}-{title}") for section in SECTIONS for title in section.sortable
]


@pytest.mark.parametrize(("section", "title"), SORT_CASES)
def test_sorting_cycle(page: Page, section: Section, title: str) -> None:
    section_page = SectionPage(page, section).open()
    sorting = TableSorting(section_page)
    initial_rows = section_page.row_texts()

    sorting.toggle(title)
    ascending = sorting.values(title)
    if len(ascending) < 2:
        pytest.skip(f"Недостаточно данных в колонке '{title}' для проверки сортировки")
    assert is_sorted(ascending), f"Нет сортировки по возрастанию: {ascending[:5]}"

    sorting.toggle(title)
    descending = sorting.values(title)
    assert is_sorted(descending, descending=True), f"Нет сортировки по убыванию: {descending[:5]}"

    sorting.toggle(title)
    assert section_page.row_texts() == initial_rows, "Сортировка не сбросилась к исходному порядку"
