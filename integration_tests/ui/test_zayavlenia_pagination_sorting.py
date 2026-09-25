"""
Комплексный тест раздела Документы → Заявления:
  - Проверка UI элементов (header, вкладки, иконки)
  - Проверка структуры таблицы (10 колонок)
  - Пагинация (10/20/50/100 строк, навигация стрелками, переход first/last)
  - Сортировка по колонкам (Наименование, Покупатель, Сумма, Дата)
"""
import re
import logging
from playwright.sync_api import Page, expect
from integration_tests.ui.config import Config
from integration_tests.ui.login_page import LoginPage
from integration_tests.ui.base_page import BasePage
from integration_tests.ui.helpers.pagination_helper import PaginationHelper
from integration_tests.ui.helpers.sorting_helper import SortingHelper
from integration_tests.ui.conftest import SoftAssert

logger = logging.getLogger(__name__)


class FinanceDocumentsStatementsPage(BasePage):
    """Page Object для раздела Документы → Заявления"""

    # =============================================================================
    # КОНФИГУРАЦИЯ КОЛОНОК (10 штук)
    # =============================================================================
    REQUIRED_COLUMNS = [
        "No.", "Наименование", "Провайдер", "Покупатель",
        "ИНН", "КПП", "Транзакция", "Сумма", "Сумма с НДС", "Дата"
    ]

    # Селекторы колонок
    COLUMN_SELECTORS = {
        "No.": "th.cdk-column-id",
        "Наименование": "th.cdk-column-name",
        "Провайдер": "th.cdk-column-provider_name",
        "Покупатель": "th.cdk-column-buyer_name",
        "ИНН": "th.cdk-column-inn",
        "КПП": "th.cdk-column-kpp",
        "Транзакция": "th.cdk-column-transaction_id",
        "Сумма": "th.cdk-column-pure_amount",
        "Сумма с НДС": "th.cdk-column-obligations_amount",
        "Дата": "th.cdk-column-date",
    }

    # =============================================================================
    # КОНФИГУРАЦИЯ СОРТИРОВКИ (колонки с ui-sort)
    # =============================================================================
    SORT_CONFIG = {
        "name": {
            "header_text": "Наименование",
            "header_selector": "th.cdk-column-name",
            "index": 1,
            "type": "text"
        },
        "buyer": {
            "header_text": "Покупатель",
            "header_selector": "th.cdk-column-buyer_name",
            "index": 3,
            "type": "text"
        },
        "amount": {
            "header_text": "Сумма",
            "header_selector": "th.cdk-column-pure_amount",
            "index": 7,
            "type": "number"
        },
        "date": {
            "header_text": "Дата",
            "header_selector": "th.cdk-column-date",
            "index": 9,
            "type": "date",
            "date_format": "%d.%m.%Y"
        }
    }

    # =============================================================================
    # КОНФИГУРАЦИЯ ПАГИНАЦИИ (nz-pagination + ui-paginator)
    # =============================================================================
    PAGINATION_CONFIG = {
        "table_rows": "table.cdk-table tbody tr:visible",
        "empty_state": "div.ant-empty",
        "paginator_label": "ui-paginator div.limit span.label",
        "paginator_options": {
            10: "ul.limit-ul li.limit-ul__item:nth-child(1) span.value",
            20: "ul.limit-ul li.limit-ul__item:nth-child(2) span.value",
            50: "ul.limit-ul li.limit-ul__item:nth-child(3) span.value",
            100: "ul.limit-ul li.limit-ul__item:nth-child(4) span.value",
        },
        "prev_arrow": "nz-pagination ul li.ant-pagination-prev button.ant-pagination-item-link",
        "next_arrow": "nz-pagination ul li.ant-pagination-next button.ant-pagination-item-link",
        "page_numbers": "nz-pagination ul li.ant-pagination-item a",
        "first_page": "nz-pagination ul li.ant-pagination-item:nth-child(2) a",
        "neutral_click": "app-content",
    }

    # =============================================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =============================================================================
    def __init__(self, page: Page):
        super().__init__(page)
        # Специфичные селекторы страницы
        self.header = page.locator("app-layout").first
        self.tabs = {
            "upd": page.locator("span.navigations__item:has-text('УПД')").first,
            "ukd": page.locator("span.navigations__item:has-text('УКД')").first,
            "invoices": page.locator("span.navigations__item:has-text('Счета на оплату')").first,
            "statements": page.locator("span.navigations__item:has-text('Заявления')").first,
        }
        self.icons = {
            "filter": page.locator("ui-filter-panel button.ant-btn-icon-only").first,
            "settings": page.locator("ui-columns-settings button.ant-btn-icon-only").first,
            "fullscreen": page.locator("ui-fullscreen-table button.ant-btn-icon-only").first,
        }
        self.table = page.locator("app-agreements-table table.cdk-table").first

    # =============================================================================
    # НАВИГАЦИЯ
    # =============================================================================
    def navigate_to_statements(self) -> None:
        """Переход в раздел Документы → Заявления"""
        logger.info("📍 Навигация: Документы → Заявления")
        self.page.locator("a.sidebar__nav-link:has-text('Документы')").first.click(
            timeout=self.action_timeout
        )
        self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)

        # Клик по вкладке "Заявления"
        self.tabs["statements"].click(timeout=self.action_timeout)
        self.page.wait_for_load_state("networkidle", timeout=15000)

    # =============================================================================
    # ПРОВЕРКИ UI
    # =============================================================================
    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы и наличия данных"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tabs["statements"]).to_be_visible(timeout=self.action_timeout)
            expect(self.table).to_be_visible(timeout=30000)
            self.wait_for_table_stable("table.cdk-table")

            # Проверяем, что таблица не пуста
            rows = self.page.locator("table.cdk-table tbody tr:visible")
            if rows.count() == 0:
                logger.warning("⚠️ Таблица пуста после загрузки")
                return False

            logger.info("✅ UI загружен и содержит данные")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка верификации: {e}")
            self.take_screenshot("verify_initial_fail")
            return False

    def verify_table_columns(self) -> bool:
        """
        Проверяет наличие всех 10 колонок таблицы.
        Использует text-based selectors для надежности.
        """
        logger.info("🔍 Проверка 10 колонок таблицы...")
        missing = []

        for col_name in self.REQUIRED_COLUMNS:
            # Используем get_by_text для поиска по тексту заголовка
            locator = self.page.get_by_text(col_name, exact=True).first
            try:
                if locator.is_visible(timeout=1000):
                    logger.debug(f"   ✅ '{col_name}' найдена")
                else:
                    missing.append(col_name)
                    logger.error(f"   ❌ '{col_name}' НЕ найдена")
            except Exception:
                missing.append(col_name)
                logger.error(f"   ❌ '{col_name}' НЕ найдена (exception)")

        if missing:
            logger.error(f"⚠️ Отсутствуют колонки: {missing}")
            return False

        logger.info(f"✅ Все {len(self.REQUIRED_COLUMNS)} колонок присутствуют")
        return True


# =============================================================================
# ТЕСТ
# =============================================================================

def test_statements_pagination_sorting(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    """
    Комплексный тест раздела Документы → Заявления:
      1. Авторизация и навигация
      2. Проверка UI (header, вкладки, иконки)
      3. Проверка структуры таблицы (10 колонок)
      4. Пагинация (10/20/50/100 строк + навигация)
      5. Сортировка по 4 колонкам (ASC → DESC → RESET)
    """
    logger.info("🚀 Старт: Пагинация и сортировка → Заявления")

    # Инициализация Page Object и хелперов
    statements_page = FinanceDocumentsStatementsPage(page)
    pagination = PaginationHelper(page, config=FinanceDocumentsStatementsPage.PAGINATION_CONFIG)
    sorting = SortingHelper(
        page,
        sort_config=FinanceDocumentsStatementsPage.SORT_CONFIG,
        table_selector="table.cdk-table",
        use_icon_click=True,  # Клик по ui-sort иконкам
        icon_selector_template='th:has-text("{name}") ui-sort'
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        statements_page.navigate_to_statements()
        take_screenshot("after_nav")

        if not statements_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")
        soft_assert.check(
            statements_page.verify_multiple_elements(statements_page.tabs, "tabs"),
            "Вкладки не отображаются", "ui:tabs"
        )
        soft_assert.check(
            statements_page.verify_multiple_elements(statements_page.icons, "icons"),
            "Не все иконки отображаются", "ui:icons"
        )
        soft_assert.check(
            statements_page.verify_table_columns(),
            "Не все 10 колонок таблицы найдены", "ui:columns"
        )

        # ==================== БЛОК 3: ПАГИНАЦИЯ ====================
        logger.info("📄 Блок 3: Пагинация")
        for count in [10, 20, 50, 100, 20]:
            try:
                pagination.change_items_per_page(count)
                soft_assert.check(
                    pagination.verify_items_per_page(count),
                    f"Неверное кол-во строк при {count}",
                    f"pagination:{count}"
                )
            except Exception as e:
                soft_assert.check(False, f"Ошибка: {e}", f"pagination:{count}")

        soft_assert.check(
            pagination.navigate_pages("next", 2), "Ошибка навигации вперёд", "pagination:next"
        )
        soft_assert.check(
            pagination.navigate_pages("prev", 2), "Ошибка навигации назад", "pagination:prev"
        )
        soft_assert.check(
            pagination.go_to_page("last"), "Ошибка перехода на последнюю", "pagination:last"
        )
        soft_assert.check(
            pagination.go_to_page("first"), "Ошибка перехода на первую", "pagination:first"
        )

        # ==================== БЛОК 4: СОРТИРОВКА ====================
        logger.info("🔍 Блок 4: Сортировка (4 колонки)")
        sorting.test_sorting_cycle("name", soft_assert)
        sorting.test_sorting_cycle("buyer", soft_assert)
        sorting.test_sorting_cycle("amount", soft_assert)
        sorting.test_sorting_cycle("date", soft_assert)

        # ==================== ФИНАЛ ====================
        take_screenshot("test_complete")

        if soft_assert.has_errors():
            logger.warning(f"⚠️ Завершено с {len(soft_assert.errors)} ошибкой(ами)")
        else:
            logger.info("🎉 Тест успешен!")

        soft_assert.report_and_raise_if_failed()

    except AssertionError:
        take_screenshot("test_fail")
        raise
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка: {e}")
        take_screenshot("test_critical_fail")
        raise AssertionError(f"Системная ошибка: {e}") from e
