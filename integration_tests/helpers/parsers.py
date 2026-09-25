"""
Разбор значений ячеек таблицы и проверка порядка сортировки.
Чистые функции без Playwright — покрыты офлайн-тестами в unit_tests.
"""

import re
from datetime import datetime
from itertools import pairwise

from integration_tests.config.sections import ValueType

_DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})(?:[ ,]+(\d{2}:\d{2}(?::\d{2})?))?")
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_EMPTY_MARKERS = {"", "-", "—"}


def normalize_text(text: str) -> str:
    """Нижний регистр, ё→е, неразрывные и множественные пробелы → один пробел."""
    text = text.replace("\xa0", " ").replace(" ", " ").lower().replace("ё", "е")
    return " ".join(text.split())


def parse_number(text: str) -> float | None:
    """'1 000,50 ₽' → 1000.5. Пробелы-разделители разрядов (в т.ч. неразрывные) убираются."""
    compact = re.sub(r"[\s\xa0 ]", "", text)
    match = _NUMBER_RE.search(compact)
    return float(match.group().replace(",", ".")) if match else None


def parse_date(text: str) -> datetime | None:
    """'31.12.2025' или '31.12.2025 14:05' → datetime (время учитывается, если есть)."""
    match = _DATE_RE.search(text)
    if not match:
        return None
    date_part, time_part = match.groups()
    if not time_part:
        return datetime.strptime(date_part, "%d.%m.%Y")
    fmt = "%d.%m.%Y %H:%M:%S" if time_part.count(":") == 2 else "%d.%m.%Y %H:%M"
    return datetime.strptime(f"{date_part} {time_part}", fmt)


def parse_cell(text: str | None, value_type: ValueType) -> str | float | datetime | None:
    """Приводит текст ячейки к сравнимому значению; пустые ячейки → None."""
    if text is None or text.strip() in _EMPTY_MARKERS:
        return None
    if value_type == ValueType.NUMBER:
        return parse_number(text)
    if value_type == ValueType.DATE:
        return parse_date(text)
    return normalize_text(text)


def parse_column(texts: list[str | None], value_type: ValueType) -> list:
    """Разбирает значения колонки, отбрасывая пустые и нераспознанные."""
    parsed = (parse_cell(t, value_type) for t in texts)
    return [v for v in parsed if v is not None]


def is_sorted(values: list, descending: bool = False) -> bool:
    return all((a >= b) if descending else (a <= b) for a, b in pairwise(values))
