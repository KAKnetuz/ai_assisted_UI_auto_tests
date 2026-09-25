"""Пагинация: размер страницы и навигация по страницам."""

import pytest
from playwright.sync_api import Page

from integration_tests.components.paginator import Paginator
from integration_tests.config.constants import PAGE_SIZES
from integration_tests.config.sections import SECTIONS, Section
from integration_tests.pages.section_page import SectionPage

pytestmark = [pytest.mark.ui, pytest.mark.pagination]

PAGINATED = [s for s in SECTIONS if s.paginated]


@pytest.mark.parametrize("size", PAGE_SIZES)
@pytest.mark.parametrize("section", PAGINATED, ids=lambda s: s.id)
def test_page_size(page: Page, section: Section, size: int) -> None:
    section_page = SectionPage(page, section).open()
    paginator = Paginator(section_page)

    paginator.set_page_size(size)
    rows = section_page.row_count()

    assert rows <= size, f"На странице {rows} строк при размере {size}"
    # Если есть следующая страница, текущая должна быть заполнена полностью —
    # иначе размер фактически не применился (раньше эта ошибка проходила незамеченной)
    if paginator.has_next_page():
        assert rows == size, f"Есть следующая страница, но строк {rows} вместо {size}"


@pytest.mark.parametrize("section", PAGINATED, ids=lambda s: s.id)
def test_page_navigation(page: Page, section: Section) -> None:
    section_page = SectionPage(page, section).open()
    paginator = Paginator(section_page)
    if not paginator.has_next_page():
        pytest.skip("В разделе одна страница данных — навигацию проверить нельзя")

    first_page_rows = section_page.row_texts()

    paginator.next()
    assert paginator.current_page == 2
    assert section_page.row_texts() != first_page_rows, "Данные не изменились после перехода вперёд"

    paginator.prev()
    assert paginator.current_page == 1
    assert section_page.row_texts() == first_page_rows, "После возврата назад данные первой страницы другие"

    last = paginator.last_page
    paginator.last()
    assert paginator.current_page == last
    assert not paginator.has_next_page(), "На последней странице кнопка «Вперёд» активна"

    paginator.first()
    assert paginator.current_page == 1
    assert section_page.row_texts() == first_page_rows
