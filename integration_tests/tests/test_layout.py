"""Структура раздела: колонки таблицы и иконки панели инструментов."""

import pytest
from playwright.sync_api import Page

from integration_tests.config.sections import SECTIONS, Section
from integration_tests.helpers.soft_assert import SoftAssert
from integration_tests.pages.section_page import SectionPage

pytestmark = [pytest.mark.ui, pytest.mark.layout]


@pytest.mark.smoke
@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.id)
def test_section_opens_with_data(page: Page, section: Section) -> None:
    section_page = SectionPage(page, section).open()
    assert section_page.row_count() > 0, f"Таблица раздела '{section.title}' пуста"


@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.id)
def test_table_columns_are_visible(page: Page, section: Section) -> None:
    section_page = SectionPage(page, section).open()
    soft = SoftAssert()
    for column in section.columns:
        soft.check(section_page.header_by_selector(column).is_visible(), "колонка не отображается", column.title)
    soft.assert_all()


@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.id)
def test_toolbar_icons_are_visible(page: Page, section: Section) -> None:
    SectionPage(page, section).open()
    soft = SoftAssert()
    for name, selector in section.icon_selectors.items():
        soft.check(page.locator(selector).first.is_visible(), "иконка не отображается", name)
    soft.assert_all()
