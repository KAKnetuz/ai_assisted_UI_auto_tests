"""
Переиспользуемый помощник для работы с фильтрами таблиц.
Поддерживает текстовые, чекбоксные и дата-фильтры.
"""
import logging
from typing import List, Optional, Dict
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config

logger = logging.getLogger(__name__)


class FilterHelper:
    """
    Хелпер для работы с фильтрами таблиц.
    Инкапсулирует логику открытия, применения и сброса фильтров.
    """

    # Базовые селекторы заголовков колонок 
    COLUMN_SELECTORS = {
        "ID": "th.cdk-column-id",
        "Наименование": "th.cdk-column-name",
        "Продукт": "th.cdk-column-product_name",
        "Провайдер": "th.cdk-column-contragent_name",
        "Платформа": "th.cdk-column-platform",
        "Тип": "th.cdk-column-type",
        "Статус": "th.cdk-column-status",
        "Создан": "th.cdk-column-created_date",
        "Срок действия": "th.cdk-column-valid_until",
    }

    # Селекторы для кнопки сброса фильтров (в порядке приоритета)
    RESET_BUTTON_SELECTORS = [
        "ui-reset-filters > button.ant-btn.reset-filter.ant-btn-icon-only",
        "button[aria-label*='reset']",
        r"button.uiTableIcons\:resetFilters",
        "button.ant-btn[title*='Сбросить']",
        "button.ant-btn[title*='Reset']",
    ]

    def __init__(
        self,
        page: Page,
        table_selector: str = "table.cdk-table",
        custom_selectors: Optional[Dict[str, str]] = None
    ):
        """
        :param page: Playwright Page
        :param table_selector: CSS-селектор таблицы
        :param custom_selectors: Словарь кастомных селекторов колонок,
                                 который объединяется с базовыми COLUMN_SELECTORS.
                                 Позволяет переиспользовать хелпер для разных разделов
                                 (Платежи, Счета, Продукты и т.д.)
        """
        self.page = page
        self.table_selector = table_selector
        self.action_timeout = Config.ACTION_TIMEOUT
        self.test_timeout = Config.TEST_TIMEOUT
        self._cell_cache = {}
        # Объединяем базовые и кастомные селекторы (кастомные имеют приоритет)
        self._column_selectors = {**self.COLUMN_SELECTORS, **(custom_selectors or {})}

    # ================= ОВЕРЛЕЙ ФИЛЬТРА =================
    def _get_overlay(self):
        """Получает локатор открытого оверлея фильтра"""
        return self.page.locator(
            "div.ant-dropdown:has(button:has-text('Применить')), "
            "div.cdk-overlay-pane:has(button:has-text('Применить'))"
        ).first

    def _wait_for_overlay_visible(self, timeout: Optional[int] = None) -> None:
        """Ожидает появления оверлея фильтра"""
        expect(self._get_overlay()).to_be_visible(timeout=timeout or self.action_timeout)

    def _apply_filter(self, overlay=None) -> None:
        """
        Универсальный метод применения фильтра:
        1. Кликает 'Применить'.
        2. Ждёт закрытия оверлея.
        3. Ждёт стабилизации таблицы.
        """
        if overlay is None:
            overlay = self._get_overlay()

        apply_btn = overlay.locator("button.ant-btn-primary:has-text('Применить')").first
        expect(apply_btn).to_be_enabled(timeout=self.action_timeout)
        apply_btn.click()

        try:
            expect(overlay).to_be_hidden(timeout=self.action_timeout)
        except PlaywrightTimeoutError:
            pass

        self.wait_for_table_stable()
        self._cell_cache.clear()

    # ================= ОЖИДАНИЯ =================
    def wait_for_table_stable(self) -> None:
        """Ожидает стабилизации таблицы после применения фильтра"""
        try:
            self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=2000)
        except PlaywrightTimeoutError:
            pass
        self.page.wait_for_timeout(300)

    # ================= ОТКРЫТИЕ ФИЛЬТРА =================
    def open_filter(self, column_name: str) -> bool:
        """
        Открывает фильтр для указанной колонки.
        Возвращает True при успехе, False при ошибке.
        """
        try:
            logger.debug(f"🔍 Открытие фильтра: {column_name}")
            self.wait_for_table_stable()

            # Получаем селектор заголовка колонки (из объединённого словаря)
            header_selector = self._column_selectors.get(
                column_name, f"th:has-text('{column_name}')"
            )
            header = self.page.locator(header_selector).first

            expect(header).to_be_visible(timeout=self.action_timeout)
            header.scroll_into_view_if_needed()
            header.hover()
            self.page.wait_for_timeout(50)

            # Ищем кнопку фильтра с фоллбэками
            filter_btn_candidates = [
                "ui-filter-wrapper button",
                "ui-filter-wrapper",
                "button[aria-label*='filter']",
                ".filter-icon",
                "svg[data-icon='filter']",
            ]
            filter_btn = None
            for selector in filter_btn_candidates:
                locator = header.locator(selector).first
                if locator.count() > 0:
                    filter_btn = locator
                    break

            if filter_btn is None:
                raise RuntimeError(f"Не найдена кнопка фильтра для колонки '{column_name}'")

            filter_btn.click(timeout=self.action_timeout)

            try:
                self._wait_for_overlay_visible(timeout=2000)
                return True
            except PlaywrightTimeoutError:
                logger.warning(f"⚠️ Первый клик не открыл фильтр, повторяем с force=True")
                filter_btn.click(timeout=self.action_timeout, force=True)
                self._wait_for_overlay_visible(timeout=3000)
                return True

        except Exception as e:
            logger.error(f"❌ Не удалось открыть фильтр '{column_name}': {e}")
            return False

    # ================= ПРИМЕНЕНИЕ ФИЛЬТРОВ =================
    def apply_text_filter(self, text: str) -> None:
        """Применяет текстовый фильтр"""
        logger.debug(f"⌨️ Текстовый фильтр: '{text}'")
        self._wait_for_overlay_visible()
        overlay = self._get_overlay()
        input_field = overlay.locator("input.ant-input").first
        expect(input_field).to_be_visible(timeout=self.action_timeout)

        input_field.fill(text)
        self.page.wait_for_timeout(100)
        self._apply_filter(overlay)

    def apply_checkbox_filter(self, values: List[str]) -> None:
        """Применяет чекбоксный фильтр (множественный выбор)"""
        logger.debug(f"☑️ Чекбокс фильтр: {values}")
        self._wait_for_overlay_visible()
        overlay = self._get_overlay()

        for val in values:
            wrapper = overlay.locator(f".ant-checkbox-wrapper:has-text('{val}')").first
            cb = wrapper.locator("input.ant-checkbox-input").first
            expect(cb).to_be_visible(timeout=self.action_timeout)
            if not cb.is_checked():
                cb.check(timeout=self.action_timeout)

        self.page.wait_for_timeout(100)
        self._apply_filter(overlay)

    def apply_date_filter(self, start_date: str, end_date: str) -> bool:
        """Применяет фильтр по диапазону дат"""
        try:
            logger.debug(f"📅 Дата фильтр: {start_date} - {end_date}")
            self._wait_for_overlay_visible()
            overlay = self._get_overlay()

            date_inputs = overlay.locator("input.ant-picker-input")
            if date_inputs.count() < 2:
                date_start = overlay.locator("input[placeholder='Начало']").first
                date_end = overlay.locator("input[placeholder='Конец']").first
            else:
                date_start = date_inputs.nth(0)
                date_end = date_inputs.nth(1)

            expect(date_start).to_be_visible(timeout=self.action_timeout)
            expect(date_end).to_be_visible(timeout=self.action_timeout)

            # Ввод начальной даты
            date_start.click()
            date_start.fill(start_date)
            self.page.keyboard.press("Tab")
            self.page.wait_for_timeout(50)

            # Ввод конечной даты
            date_end.click()
            date_end.fill(end_date)
            self.page.keyboard.press("Tab")
            self.page.wait_for_timeout(50)

            # Закрываем календарь, если открылся
            if overlay.locator(".ant-picker-dropdown").is_visible(timeout=300):
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(50)

            self._apply_filter(overlay)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка применения дата-фильтра: {e}")
            return False

    def clear_filter(self) -> None:
        """Очищает текущий фильтр (кнопка 'Очистить')"""
        logger.debug("🧹 Очистка фильтра")
        self._wait_for_overlay_visible()
        overlay = self._get_overlay()
        clear_btn = overlay.locator("button:has-text('Очистить')").first
        expect(clear_btn).to_be_visible(timeout=self.action_timeout)
        clear_btn.click()
        self._apply_filter(overlay)

    def reset_all_filters(self) -> None:
        """Сбрасывает все фильтры (глобальная кнопка или перезагрузка)"""
        logger.debug("🔄 Глобальный сброс фильтров")

        # Стратегия 1: Ищем кнопку сброса
        for selector in self.RESET_BUTTON_SELECTORS:
            locator = self.page.locator(selector).first
            if locator.is_visible(timeout=300):
                locator.click()
                self.wait_for_table_stable()
                logger.debug("✅ Фильтры сброшены через глобальную кнопку")
                self._cell_cache.clear()
                return

        # Стратегия 2: Перезагрузка страницы
        logger.warning("⚠️ Кнопка сброса не найдена. Перезагрузка страницы.")
        self.page.reload(wait_until="networkidle", timeout=self.test_timeout)
        self.wait_for_table_stable()
        self._cell_cache.clear()

    # ================= ПРОВЕРКИ ТАБЛИЦЫ =================
    def is_table_empty(self) -> bool:
        """Проверяет, пуста ли таблица"""
        try:
            self.wait_for_table_stable()
            if self.page.locator(f"{self.table_selector} div.ant-empty").is_visible(timeout=300):
                return True
            return self.count_table_rows() == 0
        except Exception as e:
            logger.warning(f"⚠️ is_table_empty error: {e}. Assuming empty.")
            return True

    def count_table_rows(self) -> int:
        """Подсчитывает количество строк в таблице через JS-evaluate"""
        try:
            self.wait_for_table_stable()
            if self.page.locator(f"{self.table_selector} div.ant-empty").is_visible(timeout=300):
                return 0

            count = self.page.locator(f"{self.table_selector} tbody tr").evaluate_all("""
                rows => {
                    return rows.filter(row => {
                        if (!row.offsetParent) return false;
                        const text = row.innerText.toLowerCase().trim();
                        const className = row.className.toLowerCase();
                        if (className.includes('no-data') || className.includes('ant-table-placeholder')) return false;
                        if (text.includes('нет данных') || text.includes('no data') || 
                            text.includes('nothing found') || text.includes('записи отсутствуют')) return false;
                        return text.length > 5;
                    }).length;
                }
            """)
            logger.debug(f"📊 Реальных записей найдено: {count}")
            return int(count)
        except Exception as e:
            logger.error(f"❌ Error counting rows: {e}")
            return 0

    def get_first_non_empty_cell_text(self, col_index: int, max_rows: int = 10) -> str:
        """
        Получает текст первой непустой ячейки в указанной колонке.
        Перебирает строки, пока не найдёт заполненное значение (с кэшированием).
        Используется в test_offers_filtering.py.
        """
        cache_key = f"col_{col_index}"
        if cache_key in self._cell_cache:
            return self._cell_cache[cache_key]

        try:
            if self.is_table_empty():
                return ""

            rows = self.page.locator(f"{self.table_selector} tbody tr")
            limit = min(rows.count(), max_rows)

            for i in range(limit):
                row = rows.nth(i)
                if not row.is_visible():
                    continue
                cell = row.locator(f"td:nth-child({col_index})")
                if cell.count() > 0:
                    text = cell.text_content().strip()
                    if text and len(text) > 0:
                        self._cell_cache[cache_key] = text
                        return text
            return ""
        except Exception as e:
            logger.error(f"Ошибка при поиске непустого значения: {e}")
            return ""

    def get_first_row_cell_text(self, col_index: int) -> str:
        """
        Получает текст ячейки из первой видимой строки таблицы.
        В отличие от get_first_non_empty_cell_text, не ищет по всем строкам,
        а берёт именно первую строку.
        Используется в test_payments_filtering.py.
        """
        try:
            rows = self.page.locator(f"{self.table_selector} tbody tr:visible")
            expect(rows.first).to_be_visible(timeout=self.action_timeout)
            cell = rows.first.locator(f"td:nth-child({col_index})")
            text = cell.text_content(timeout=self.action_timeout)
            return text.strip() if text else ""
        except Exception as e:
            logger.debug(f"⚠️ get_first_row_cell_text error: {e}")
            return ""
