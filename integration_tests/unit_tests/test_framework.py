"""
Офлайн-тесты самого фреймворка (без браузера и стенда).
Запускаются в CI: ловят поломки парсинга ячеек, проверки сортировки,
описаний разделов, мягких проверок и маскирования.
"""

from datetime import datetime

import pytest

from integration_tests.config.constants import PAGE_SIZES, TOOLBAR_ICONS
from integration_tests.config.sections import SECTIONS, Column, ValueType
from integration_tests.config.settings import Settings
from integration_tests.helpers.parsers import is_sorted, normalize_text, parse_cell, parse_column
from integration_tests.helpers.soft_assert import SoftAssert
from integration_tests.utils.logger import mask_sensitive


# ==================== ПАРСИНГ ЯЧЕЕК ====================
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 000,50 ₽", 1000.5),
        ("1\xa0234\xa0567", 1234567.0),  # неразрывные пробелы — раньше значение терялось
        ("-15.25", -15.25),
        ("42", 42.0),
    ],
)
def test_parse_number(text: str, expected: float) -> None:
    assert parse_cell(text, ValueType.NUMBER) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("31.12.2025", datetime(2025, 12, 31)),
        ("01.02.2026 14:05", datetime(2026, 2, 1, 14, 5)),
        ("01.02.2026, 14:05:30", datetime(2026, 2, 1, 14, 5, 30)),
    ],
)
def test_parse_date(text: str, expected: datetime) -> None:
    assert parse_cell(text, ValueType.DATE) == expected


@pytest.mark.parametrize("empty", [None, "", " ", "-", "—"])
def test_empty_cells_are_skipped(empty: str | None) -> None:
    assert parse_cell(empty, ValueType.TEXT) is None


def test_parse_column_drops_empty_and_unparsed() -> None:
    assert parse_column(["10", "-", "abc", "2"], ValueType.NUMBER) == [10.0, 2.0]


def test_normalize_text() -> None:
    assert normalize_text("  Отменён\xa0 ЗАКАЗ ") == "отменен заказ"


# ==================== ПРОВЕРКА СОРТИРОВКИ ====================
@pytest.mark.parametrize(
    ("values", "descending", "expected"),
    [
        ([1, 2, 2, 3], False, True),
        ([3, 1, 2], False, False),
        ([3, 2, 2, 1], True, True),
        ([1, 3], True, False),
        ([], False, True),
    ],
)
def test_is_sorted(values: list, descending: bool, expected: bool) -> None:
    assert is_sorted(values, descending=descending) is expected


def test_text_sort_ignores_case_and_yo() -> None:
    values = parse_column(["ёлка", "Ель", "Ёж"], ValueType.TEXT)
    assert values == ["елка", "ель", "еж"]


# ==================== ОПИСАНИЯ РАЗДЕЛОВ ====================
def test_section_ids_are_unique() -> None:
    ids = [s.id for s in SECTIONS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.id)
def test_section_references_declared_columns(section) -> None:
    referenced = [
        *section.sortable,
        *section.text_filters,
        *(f.column for f in section.checkbox_filters),
        *(f.column for f in section.date_filters),
    ]
    for title in referenced:
        section.column(title)  # KeyError, если колонки нет в описании


@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.id)
def test_section_is_navigable(section) -> None:
    assert section.menu or section.nav_selector, "Не задан способ перехода в раздел"
    assert set(section.icons) <= set(TOOLBAR_ICONS)


@pytest.mark.parametrize("section", SECTIONS, ids=lambda s: s.id)
def test_date_filters_use_date_columns(section) -> None:
    for f in section.date_filters:
        assert section.column(f.column).type == ValueType.DATE


def test_column_header_selector() -> None:
    assert Column("Статус", "status").header_selector == "th.cdk-column-status"
    assert Column("Дата").header_selector == "th:has-text('Дата')"


def test_page_sizes_are_ascending() -> None:
    assert list(PAGE_SIZES) == sorted(PAGE_SIZES)


# ==================== НАСТРОЙКИ ====================
def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASE_URL", "https://stand.example.org")
    monkeypatch.setenv("IGNORE_HTTPS_ERRORS", "true")
    s = Settings(_env_file=None)
    assert s.context_args["base_url"] == "https://stand.example.org"
    assert s.context_args["ignore_https_errors"] is True


# ==================== SOFT ASSERT ====================
def test_soft_assert_collects_all_errors() -> None:
    soft = SoftAssert()
    soft.check(True, "ok", "a")
    soft.check(False, "first", "b")
    soft.check(False, "second", "c")
    with pytest.raises(AssertionError, match=r"Найдено ошибок: 2[\s\S]*\[b\] first[\s\S]*\[c\] second"):
        soft.assert_all()


# ==================== МАСКИРОВАНИЕ ====================
@pytest.mark.parametrize(
    "text",
    [
        "password=SECRET-VALUE-123",
        '{"token": "SECRET-VALUE-123"}',
        "Authorization: Bearer SECRET-VALUE-123",
    ],
    ids=["query", "json", "bearer"],
)
def test_sensitive_values_are_masked(text: str) -> None:
    assert "SECRET-VALUE-123" not in mask_sensitive(text)


def test_non_sensitive_values_are_kept() -> None:
    assert mask_sensitive("username=demo_user") == "username=demo_user"
