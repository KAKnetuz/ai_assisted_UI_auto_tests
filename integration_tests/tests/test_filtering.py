"""
Фильтры колонок. Проверяется не только «таблица не пуста», но и то,
что каждая строка результата действительно соответствует фильтру.
"""

from datetime import datetime, timedelta

import pytest
from playwright.sync_api import Page

from integration_tests.components.table_filter import TableFilter
from integration_tests.config.constants import (
    DATE_FORMAT,
    FUTURE_PERIOD_END_DAYS,
    FUTURE_PERIOD_START_DAYS,
    NON_EXISTENT_TEXT,
    PARTIAL_SEARCH_LENGTH,
    PAST_PERIOD_DAYS,
)
from integration_tests.config.sections import SECTIONS, CheckboxFilter, DateFilter, Section
from integration_tests.helpers.parsers import normalize_text, parse_date
from integration_tests.pages.section_page import SectionPage

pytestmark = [pytest.mark.ui, pytest.mark.filtering]

TEXT_CASES = [pytest.param(s, title, id=f"{s.id}-{title}") for s in SECTIONS for title in s.text_filters]
CHECKBOX_CASES = [pytest.param(s, f, id=f"{s.id}-{f.column}") for s in SECTIONS for f in s.checkbox_filters]
DATE_CASES = [pytest.param(s, f, id=f"{s.id}-{f.column}") for s in SECTIONS for f in s.date_filters]
FUTURE_DATE_CASES = [p for p in DATE_CASES if p.values[1].future_is_empty]


def _open(page: Page, section: Section) -> tuple[SectionPage, TableFilter]:
    section_page = SectionPage(page, section).open()
    return section_page, TableFilter(section_page)


def _sample_value(section_page: SectionPage, title: str) -> str:
    value = section_page.first_value(title)
    if not value:
        pytest.skip(f"В колонке '{title}' нет данных для фильтрации")
    return value


# ==================== ТЕКСТОВЫЕ ФИЛЬТРЫ ====================
@pytest.mark.parametrize("partial", [False, True], ids=["full", "partial"])
@pytest.mark.parametrize(("section", "title"), TEXT_CASES)
def test_text_filter_matches_rows(page: Page, section: Section, title: str, partial: bool) -> None:
    section_page, table_filter = _open(page, section)
    value = _sample_value(section_page, title)
    query = value[:PARTIAL_SEARCH_LENGTH] if partial else value

    table_filter.apply_text(title, query)

    cells = section_page.column_texts(title)
    assert cells, f"Нет результатов по запросу '{query}', хотя значение '{value}' есть в таблице"
    mismatched = [c for c in cells if normalize_text(query) not in normalize_text(c or "")]
    assert not mismatched, f"Строки не содержат '{query}': {mismatched[:5]}"


@pytest.mark.parametrize(("section", "title"), TEXT_CASES)
def test_text_filter_non_existent_value(page: Page, section: Section, title: str) -> None:
    section_page, table_filter = _open(page, section)
    table_filter.apply_text(title, NON_EXISTENT_TEXT)
    assert section_page.row_count() == 0, "Таблица не пуста для несуществующего значения"


# ==================== ЧЕКБОКСНЫЕ ФИЛЬТРЫ ====================
@pytest.mark.parametrize("multiple", [False, True], ids=["single", "multiple"])
@pytest.mark.parametrize(("section", "checkbox"), CHECKBOX_CASES)
def test_checkbox_filter(page: Page, section: Section, checkbox: CheckboxFilter, multiple: bool) -> None:
    section_page, table_filter = _open(page, section)
    selected = checkbox.options[:2] if multiple else checkbox.options[:1]

    table_filter.apply_checkboxes(checkbox.column, selected)

    cells = section_page.column_texts(checkbox.column)
    if not cells:
        pytest.skip(f"Нет записей со значениями {selected}")
    allowed = {normalize_text(o) for o in selected}
    unexpected = sorted({c for c in cells if normalize_text(c or "") not in allowed})
    assert not unexpected, f"В выборке по {selected} есть лишние значения: {unexpected}"


# ==================== ФИЛЬТРЫ ПО ДАТЕ ====================
@pytest.mark.parametrize(("section", "date_filter"), DATE_CASES)
def test_date_filter_past_period(page: Page, section: Section, date_filter: DateFilter) -> None:
    section_page, table_filter = _open(page, section)
    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=PAST_PERIOD_DAYS)

    table_filter.apply_date_range(date_filter.column, start.strftime(DATE_FORMAT), end.strftime(DATE_FORMAT))

    dates = [parse_date(c) for c in section_page.column_texts(date_filter.column) if c]
    if not dates:
        pytest.skip(f"Нет записей за последние {PAST_PERIOD_DAYS} дней")
    out_of_range = [d for d in dates if d is None or not start <= d < end + timedelta(days=1)]
    assert not out_of_range, f"Даты вне периода {start:%d.%m.%Y}–{end:%d.%m.%Y}: {out_of_range[:5]}"


@pytest.mark.parametrize(("section", "date_filter"), FUTURE_DATE_CASES)
def test_date_filter_future_period_is_empty(page: Page, section: Section, date_filter: DateFilter) -> None:
    section_page, table_filter = _open(page, section)
    today = datetime.now()
    start = (today + timedelta(days=FUTURE_PERIOD_START_DAYS)).strftime(DATE_FORMAT)
    end = (today + timedelta(days=FUTURE_PERIOD_END_DAYS)).strftime(DATE_FORMAT)

    table_filter.apply_date_range(date_filter.column, start, end)

    assert section_page.row_count() == 0, f"Есть записи с датой '{date_filter.column}' в будущем ({start}–{end})"
