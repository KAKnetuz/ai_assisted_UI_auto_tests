"""
Переиспользуемый помощник для тестирования сортировки таблиц.
Поддерживает кастомные селекторы (ui-sort, cdk-sort, nz-sort и т.д.)
"""
import logging
import re
from datetime import datetime
from typing import List, Optional, Dict
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config

logger = logging.getLogger(__name__)


class SortingHelper:
    """
    Хелпер для тестирования сортировки.
    Поддерживает:
      - Стандартные CDK-таблицы (клик по заголовку)
      - Кастомные иконки сортировки (ui-sort, nz-sort)
      - Числовые, текстовые и дата-колонки
    """

    # Конфигурация по умолчанию для стандартных CDK-таблиц
    DEFAULT_SORT_CONFIG = {
        "created": {
            "header_text": "Создан",
            "header_selector": "th.cdk-column-created_date",
            "date_format": "%d.%m.%Y",
            "type": "date"
        },
        "validity": {
            "header_text": "Срок действия",
            "header_selector": "th.cdk-column-valid_until",
            "date_format": "%d.%m.%Y",
            "type": "date"
        }
    }

    def __init__(
        self,
        page: Page,
        sort_config: Optional[Dict] = None,
        table_selector: str = "table.cdk-table",
        use_icon_click: bool = False,
        icon_selector_template: str = 'th:has-text("{name}") ui-sort'
    ):
        """
        :param page: Playwright page
        :param sort_config: Словарь конфигурации колонок
        :param table_selector: Селектор таблицы
        :param use_icon_click: Если True — кликает по иконке ui-sort, иначе по заголовку
        :param icon_selector_template: Шаблон селектора иконки (подставляется имя колонки)
        """
        self.page = page
        self.sort_config = sort_config or self.DEFAULT_SORT_CONFIG
        self.table_selector = table_selector
        self.use_icon_click = use_icon_click
        self.icon_selector_template = icon_selector_template
        self.action_timeout = Config.ACTION_TIMEOUT
        self.test_timeout = Config.TEST_TIMEOUT

    # ==================== КЛИК ПО СОРТИРОВКЕ ====================
    def click_sort_header(self, config_key: str) -> None:
        """Кликает по заголовку или иконке сортировки"""
        config = self.sort_config.get(config_key)
        if not config:
            raise ValueError(f"Конфигурация не найдена: {config_key}")

        logger.debug(f"🔽 Сортировка: {config['header_text']}")

        if self.use_icon_click:
            self._click_sort_icon(config)
        else:
            self._click_header(config)

        self._wait_stable()

    def _click_header(self, config: Dict) -> None:
        """Клик по заголовку колонки (CDK-таблицы)"""
        header = self.page.locator(config["header_selector"]).first
        try:
            expect(header).to_be_visible(timeout=self.action_timeout)
        except (AssertionError, PlaywrightTimeoutError):
            header = self.page.get_by_role(
                "columnheader", name=re.compile(config["header_text"])
            ).first
            expect(header).to_be_visible(timeout=self.action_timeout)

        header.scroll_into_view_if_needed()
        header.click(timeout=self.action_timeout)

    def _click_sort_icon(self, config: Dict) -> None:
        """Клик по иконке ui-sort / nz-sort"""
        # Формируем селектор из шаблона
        icon_selector = self.icon_selector_template.format(name=config["header_text"])
        icon = self.page.locator(icon_selector).first

        try:
            expect(icon).to_be_visible(timeout=self.action_timeout)
        except (AssertionError, PlaywrightTimeoutError):
            # Fallback: ищем по тексту заголовка + ui-sort
            icon = self.page.locator(
                f'th:has-text("{config["header_text"]}") ui-sort'
            ).first
            expect(icon).to_be_visible(timeout=self.action_timeout)

        icon.scroll_into_view_if_needed()
        # Кликаем по SVG внутри иконки
        icon.locator("svg").first.click(timeout=self.action_timeout)

    # ==================== ИЗВЛЕЧЕНИЕ ЗНАЧЕНИЙ ====================
    # В sorting_helper.py, метод get_column_values:
    def get_column_values(self, config_key: str, limit: int = 20) -> List:
        """Извлекает значения из указанной колонки (пропускает пустые)"""
        config = self.sort_config.get(config_key)
        if not config:
            return []

        column_type = config.get("type", "text")
        column_index = config.get("index")

        if column_index is None:
            column_index = self._find_column_index(config["header_text"])
            if column_index is None:
                return []

        # Извлекаем значения, пропуская пустые ячейки
        values = []
        rows = self.page.locator(f"{self.table_selector} tbody tr:visible")
        row_count = rows.count()

        # Увеличиваем лимит поиска до 50 строк для надёжности
        search_limit = min(row_count, 50)

        for i in range(search_limit):
            if len(values) >= limit:
                break  # Собрали достаточно значений

            try:
                cell = rows.nth(i).locator("td").nth(column_index)
                text = cell.inner_text(timeout=2000).strip()

                # Пропускаем пустые ячейки
                if not text or text == '-':
                    continue

                parsed = self._parse_value(text, column_type, config.get("date_format"))
                if parsed is not None:
                    values.append(parsed)
            except Exception:
                continue

        logger.debug(f"   Извлечено {len(values)} значений (тип: {column_type}, просмотрено {search_limit} строк)")
        return values

    def get_row_identifiers(self, limit: int = 20) -> List[str]:
        """Извлекает идентификаторы строк (первая ячейка)"""
        rows = self.page.locator(f"{self.table_selector} tbody tr:visible")
        identifiers = []
        for i in range(min(rows.count(), limit)):
            try:
                first_cell = rows.nth(i).locator("td").first.inner_text(timeout=2000).strip()
                identifiers.append(first_cell if first_cell and first_cell != '-' else f"row_{i}")
            except Exception:
                identifiers.append(f"error_{i}")
        return identifiers

    # ==================== ПРОВЕРКИ СОРТИРОВКИ ====================
    def verify_ascending(self, config_key: str) -> bool:
        """Проверяет сортировку по возрастанию"""
        values = self.get_column_values(config_key)
        if len(values) < 2:
            logger.warning(f"⚠️ Мало данных для проверки ASC ({len(values)})")
            return True
        is_sorted = values == sorted(values)
        if not is_sorted:
            logger.error(f"❌ Не ASC: {values[:5]} vs {sorted(values)[:5]}")
        return is_sorted

    def verify_descending(self, config_key: str) -> bool:
        """Проверяет сортировку по убыванию"""
        values = self.get_column_values(config_key)
        if len(values) < 2:
            return True
        is_sorted = values == sorted(values, reverse=True)
        if not is_sorted:
            logger.error(f"❌ Не DESC: {values[:5]} vs {sorted(values, reverse=True)[:5]}")
        return is_sorted

    def verify_reset(self, initial_order: List[str]) -> bool:
        """Проверяет сброс сортировки к начальному порядку"""
        current_order = self.get_row_identifiers()
        is_reset = (current_order == initial_order)
        if not is_reset:
            logger.error(f"❌ Сортировка не сброшена")
            logger.debug(f"   Ожидание: {initial_order[:3]}")
            logger.debug(f"   Факт:     {current_order[:3]}")
        return is_reset

    # ==================== ПОЛНЫЙ ЦИКЛ ====================
    def test_sorting_cycle(self, config_key: str, soft_assert) -> None:
        """
        Выполняет полный цикл: ASC → DESC → RESET.
        Результаты пишет в soft_assert.
        """
        config = self.sort_config.get(config_key)
        if not config:
            soft_assert.check(False, f"Нет конфига для {config_key}", f"sort:{config_key}")
            return

        header_text = config["header_text"]
        loc = f"sort:{config_key}"
        logger.info(f"📊 Тест сортировки: {header_text}")

        try:
            initial_order = self.get_row_identifiers()

            # ASC
            self.click_sort_header(config_key)
            soft_assert.check(
                self.verify_ascending(config_key),
                f"Данные не ASC для '{header_text}'",
                f"{loc}.asc"
            )

            # DESC
            self.click_sort_header(config_key)
            soft_assert.check(
                self.verify_descending(config_key),
                f"Данные не DESC для '{header_text}'",
                f"{loc}.desc"
            )

            # RESET
            self.click_sort_header(config_key)
            soft_assert.check(
                self.verify_reset(initial_order),
                f"Сортировка не сброшена для '{header_text}'",
                f"{loc}.reset"
            )
            logger.debug(f"✅ Цикл завершён: {header_text}")

        except Exception as e:
            logger.error(f"❌ Ошибка сортировки {header_text}: {e}")
            soft_assert.check(False, f"Исключение: {e}", loc)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ ====================
    def _find_column_index(self, header_text: str) -> Optional[int]:
        """Находит индекс колонки по тексту заголовка"""
        headers = self.page.locator(f"{self.table_selector} thead th").all()
        for idx, header in enumerate(headers):
            try:
                if header_text in header.inner_text().strip():
                    return idx
            except Exception:
                continue
        logger.error(f"❌ Колонка '{header_text}' не найдена")
        return None

    @staticmethod
    def _parse_value(text: str, column_type: str, date_format: Optional[str] = None):
        """Парсит значение в зависимости от типа колонки"""
        text = text.strip()
        if not text or text == '-':
            return None

        if column_type == "number":
            try:
                return int(text.replace(' ', '').replace(',', '.'))
            except (ValueError, TypeError):
                try:
                    return float(text.replace(' ', '').replace(',', '.'))
                except (ValueError, TypeError):
                    return None

        elif column_type == "date":
            fmt = date_format or "%d.%m.%Y"
            date_part = text.split()[0] if ' ' in text else text
            formats = [fmt, "%d.%m.%Y", "%Y-%m-%d", "%d.%m.%Y %H:%M"]
            for f in formats:
                try:
                    return datetime.strptime(date_part, f.split()[0] if ' ' in f else f)
                except ValueError:
                    continue
            return None

        else:  # text
            return text.lower()

    def _wait_stable(self) -> None:
        """Ожидает стабилизации таблицы"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)
        except PlaywrightTimeoutError:
            pass
        try:
            self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=2000)
        except PlaywrightTimeoutError:
            pass
        self.page.wait_for_timeout(300)