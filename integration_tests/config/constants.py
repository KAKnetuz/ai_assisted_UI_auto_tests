"""Общие константы UI-тестов."""

DATE_FORMAT = "%d.%m.%Y"

# Доступные размеры страницы в пагинаторе
PAGE_SIZES = (10, 20, 50, 100)

NON_EXISTENT_TEXT = "ZZZ-NON-EXISTENT-VALUE-ZZZ"
PARTIAL_SEARCH_LENGTH = 3

# Период для проверки фильтров по дате
PAST_PERIOD_DAYS = 30
FUTURE_PERIOD_START_DAYS = 90
FUTURE_PERIOD_END_DAYS = 120

# Сколько строк таблицы анализировать при проверке сортировки
SORT_SAMPLE_SIZE = 20

# Общие селекторы UI-кита (обобщены для портфолио)
APP_ROOT = "app-layout"
SIDEBAR_LINK = "a.sidebar__nav-link"
SECTION_TAB = "span.navigations__item"
SPINNER = ".ant-spin-spinning"
EMPTY_STATE = "div.ant-empty"

TOOLBAR_ICONS = {
    "export": "app-export button.ant-btn-icon-only",
    "filter": "ui-filter-panel button.ant-btn-icon-only",
    "settings": "ui-columns-settings button.ant-btn-icon-only",
    "fullscreen": "ui-fullscreen-table button.ant-btn-icon-only",
}
