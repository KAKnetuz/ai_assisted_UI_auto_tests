"""
Комплексный тест раздела Документы → УКД:
  - Проверка UI элементов (header, вкладки, иконки)
  - Проверка структуры таблицы (12 колонок)
  - Пагинация (10/20/50/100 строк, навигация стрелками, переход first/last)
  - Сортировка по колонке Дата
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


class FinanceDocumentsUKDPage(BasePage):
    """Page Object для раздела Документы → УКД"""

    # =============================================================================
    # КОНФИГУРАЦИЯ КОЛОНОК (12 штук)
    # =============================================================================
    REQUIRED_COLUMNS = [
        "No.", "Наименование", "Сумма", "Сумма с НДС", "Провайдер",
        "Покупатель", "ИНН", "КПП", "Заказ", "Транзакция", "УПД", "Дата"
    ]

    # Селекторы колонок 
    COLUMN_SELECTORS = {
        "No.": "th:has-text('No.')",
        "Наименование": "th:has-text('Наименование')",
        "Сумма": "th:has-text('Сумма')",
        "Сумма с НДС": "th:has-text('Сумма с НДС')",
        "Провайдер": "th:has-text('Провайдер')",
        "Покупатель": "th:has-text('Покупатель')",
        "ИНН": "th:has-text('ИНН')",
        "КПП": "th:has-text('КПП')",
        "Заказ": "th:has-text('Заказ')",
        "Транзакция": "th:has-text('Транзакция')",
        "УПД": "th:has-text('УПД')",
        "Дата": "th:has-text('Дата')",
    }

    # =============================================================================
    # КОНФИГУРАЦИЯ СОРТИРОВКИ 
    # =============================================================================
    SORT_CONFIG = {
        "date": {
            "header_text": "Дата",
            "header_selector": "th:has-text('Дата')",
            "index": 11,
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
            "claims": page.locator("span.navigations__item:has-text('Заявления')").first,
        }
        self.icons = {
            "filter": page.locator("ui-filter-panel button.ant-btn-icon-only").first,
            "settings": page.locator("ui-columns-settings button.ant-btn-icon-only").first,
            "fullscreen": page.locator("ui-fullscreen-table button.ant-btn-icon-only").first,
        }
        self.table = page.locator("app-bill-corrections-table table.cdk-table").first

    # =============================================================================
    # НАВИГАЦИЯ
    # =============================================================================
    def navigate_to_ukd_documents(self) -> None:
        """Переход в раздел Документы → УКД"""
        logger.info("📍 Навигация: Документы → УКД")
        self.page.locator("a.sidebar__nav-link:has-text('Документы')").first.click(
            timeout=self.action_timeout
        )
        self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)

        # Клик по вкладке "УКД"
        self.tabs["ukd"].click(timeout=self.action_timeout)
        self.page.wait_for_load_state("networkidle", timeout=15000)

    # =============================================================================
    # ПРОВЕРКИ UI
    # =============================================================================
    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы и наличия данных"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tabs["ukd"]).to_be_visible(timeout=self.action_timeout)
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
        Проверяет наличие всех 12 колонок таблицы.
        Использует text-based selectors (get_by_text) для надёжности.
        """
        logger.info("🔍 Проверка 12 колонок таблицы...")
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

def test_ukd_documents_pagination_sorting(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    """
    Комплексный тест раздела Документы → УКД:
      1. Авторизация и навигация
      2. Проверка UI (header, вкладки, иконки)
      3. Проверка структуры таблицы (12 колонок)
      4. Пагинация (10/20/50/100 строк + навигация)
      5. Сортировка по колонке Дата (ASC → DESC → RESET)
    """
    logger.info("🚀 Старт: Пагинация и сортировка → УКД")

    # Инициализация Page Object и хелперов
    ukd_page = FinanceDocumentsUKDPage(page)
    pagination = PaginationHelper(page, config=FinanceDocumentsUKDPage.PAGINATION_CONFIG)
    sorting = SortingHelper(
        page,
        sort_config=FinanceDocumentsUKDPage.SORT_CONFIG,
        table_selector="table.cdk-table",
        use_icon_click=True,  
        icon_selector_template='th:has-text("{name}") ui-sort'
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        ukd_page.navigate_to_ukd_documents()
        take_screenshot("after_nav")

        if not ukd_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")
        soft_assert.check(
            ukd_page.verify_multiple_elements(ukd_page.tabs, "tabs"),
            "Вкладки не отображаются", "ui:tabs"
        )
        soft_assert.check(
            ukd_page.verify_multiple_elements(ukd_page.icons, "icons"),
            "Не все иконки отображаются", "ui:icons"
        )
        soft_assert.check(
            ukd_page.verify_table_columns(),
            "Не все 12 колонок таблицы найдены", "ui:columns"
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
        logger.info("🔍 Блок 4: Сортировка (колонка Дата)")
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
