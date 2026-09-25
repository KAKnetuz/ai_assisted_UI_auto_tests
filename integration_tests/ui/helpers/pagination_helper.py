import logging
from typing import Optional
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config

logger = logging.getLogger(__name__)


class PaginationHelper:
    """
    Переиспользуемый помощник для тестирования пагинации.
    Работает с любыми таблицами, имеющими стандартный paginator.
    """

    def __init__(self, page: Page, config: Optional[dict] = None):
        """
        config — словарь с селекторами. Если не передан, используются дефолтные.
        Пример config:
        {
            "table_rows": "table.cdk-table tbody tr:visible",
            "empty_state": "div.ant-empty",
            "paginator_label": "ui-paginator div.limit span.label",
            "paginator_options": {
                10: "ul.limit-ul li.limit-ul__item:nth-child(1) span.value",
                ...
            },
            "prev_arrow": "li.ant-pagination-prev button",
            "next_arrow": "li.ant-pagination-next button",
            "page_numbers": "li.ant-pagination-item a",
            "first_page": "li.ant-pagination-item[title='1'] a",
            "neutral_click": "app-layout"
        }
        """
        self.page = page
        self.action_timeout = Config.ACTION_TIMEOUT
        self.test_timeout = Config.TEST_TIMEOUT
        self.config = config or self._default_config()

    @staticmethod
    def _default_config() -> dict:
        """Селекторы по умолчанию"""
        return {
            "table_rows": "table tbody tr:visible",
            "empty_state": "div.ant-empty",
            "paginator_label": "ui-paginator div.limit span.label",
            "paginator_options": {
                10: "ul.limit-ul li.limit-ul__item:nth-child(1) span.value",
                20: "ul.limit-ul li.limit-ul__item:nth-child(2) span.value",
                50: "ul.limit-ul li.limit-ul__item:nth-child(3) span.value",
                100: "ul.limit-ul li.limit-ul__item:nth-child(4) span.value",
            },
            "prev_arrow": "li.ant-pagination-prev button",
            "next_arrow": "li.ant-pagination-next button",
            "page_numbers": "li.ant-pagination-item a",
            "first_page": "li.ant-pagination-item[title='1'] a",
            "neutral_click": "app-layout",
        }

    # ==================== ПОДСЧЁТ СТРОК ====================
    def count_rows(self) -> int:
        """Подсчитывает видимые строки таблицы (с защитой от пустых)"""
        try:
            rows = self.page.locator(self.config["table_rows"])
            if self.page.locator(self.config["empty_state"]).first.is_visible(timeout=1000):
                return 0

            valid_count = 0
            for i in range(rows.count()):
                try:
                    text = rows.nth(i).inner_text(timeout=2000).strip()
                    if text and len(text) > 5:
                        valid_count += 1
                except PlaywrightTimeoutError:
                    continue
            return valid_count
        except Exception as e:
            logger.error(f"⚠️ Ошибка подсчёта строк: {e}")
            return 0

    # ==================== ИЗМЕНЕНИЕ РАЗМЕРА СТРАНИЦЫ ====================
    def change_items_per_page(self, count: int) -> None:
        """Меняет количество строк на странице"""
        option_selector = self.config["paginator_options"].get(count)
        if not option_selector:
            raise ValueError(f"Неизвестное значение: {count}. Доступные: {list(self.config['paginator_options'].keys())}")

        # Открываем dropdown
        self.page.locator(self.config["paginator_label"]).first.click(timeout=self.action_timeout)
        self.page.wait_for_selector("ul.limit-ul", state="visible", timeout=self.action_timeout)

        # Выбираем опцию
        self.page.locator(option_selector).first.click(timeout=self.action_timeout)

        # Закрываем dropdown кликом в нейтральную область
        self.page.locator(self.config["neutral_click"]).first.click(
            position={"x": 10, "y": 10}, timeout=self.action_timeout
        )

        # Ждём обновления таблицы
        self._wait_stable()
        logger.debug(f"✅ Установлено {count} строк/страница")

    def verify_items_per_page(self, expected_max: int) -> bool:
        """Проверяет, что строк не больше ожидаемого"""
        actual = self.count_rows()
        is_ok = actual <= expected_max
        if not is_ok:
            logger.error(f"❌ Ожидалось ≤ {expected_max}, получено: {actual}")
        return is_ok

    # ==================== НАВИГАЦИЯ ====================
    def navigate_pages(self, direction: str, steps: int = 1) -> bool:
        """Навигация стрелками вперёд/назад"""
        arrow_selector = self.config["next_arrow"] if direction == "next" else self.config["prev_arrow"]
        arrow = self.page.locator(arrow_selector).first
        arrow_name = "Вперёд" if direction == "next" else "Назад"

        try:
            for i in range(steps):
                if not arrow.is_enabled():
                    logger.debug(f"ℹ️ Кнопка '{arrow_name}' неактивна")
                    break

                # Запоминаем первую строку ДО клика
                first_row_before = self._get_first_row_text()

                arrow.click(timeout=self.action_timeout)

                # Проверяем, что данные обновились
                if first_row_before:
                    try:
                        rows = self.page.locator(self.config["table_rows"])
                        expect(rows.first).not_to_have_text(first_row_before, timeout=self.test_timeout)
                    except (AssertionError, PlaywrightTimeoutError):
                        logger.warning(f"⚠️ Данные не изменились после '{arrow_name}'")

                self._wait_stable()
                logger.debug(f"✅ {arrow_name} ({i + 1}/{steps})")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка навигации '{direction}': {e}")
            return False

    def go_to_page(self, page_number: str) -> bool:
        """Переход на первую/последнюю страницу"""
        if page_number == "last":
            locator = self.page.locator(self.config["page_numbers"]).last
            name = "последнюю"
        else:
            locator = self.page.locator(self.config["first_page"]).first
            name = "первую"

        try:
            first_row_before = self._get_first_row_text()
            locator.click(timeout=self.action_timeout)

            if first_row_before:
                try:
                    rows = self.page.locator(self.config["table_rows"])
                    expect(rows.first).not_to_have_text(first_row_before, timeout=self.test_timeout)
                except (AssertionError, PlaywrightTimeoutError):
                    logger.warning(f"⚠️ Данные не изменились при переходе на {name}")

            self._wait_stable()
            logger.debug(f"✅ Перешли на {name} страницу")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка перехода на {name}: {e}")
            return False

    # ==================== ВСПОМОГАТЕЛЬНЫЕ ====================
    def _get_first_row_text(self) -> str:
        """Получает текст первой строки таблицы"""
        try:
            return self.page.locator(self.config["table_rows"]).first.inner_text(timeout=2000)
        except PlaywrightTimeoutError:
            return ""

    def _wait_stable(self) -> None:
        """Ожидает стабилизации таблицы"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)
        except PlaywrightTimeoutError:
            pass
        try:
            self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=10000)
        except PlaywrightTimeoutError:
            pass
