"""
Тест пагинации и сортировки раздела Уведомления.
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


class FinanceNotificationsPage(BasePage):
    """Page Object для раздела Уведомления"""

    # Конфигурация сортируемых колонок
    SORT_CONFIG = {
        "id": {
            "header_text": "No.",
            "header_selector": 'th:has-text("No.")',
            "index": 0,
            "type": "number"
        },
        "date": {
            "header_text": "Дата",
            "header_selector": 'th:has-text("Дата")',
            "index": 1,
            "type": "date",
            "date_format": "%d.%m.%Y"
        },
        "theme": {
            "header_text": "Тема уведомления",
            "header_selector": 'th:has-text("Тема уведомления")',
            "index": 2,
            "type": "text"
        }
    }

    # Кастомные селекторы пагинации (nz-pagination + ui-paginator)
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

    REQUIRED_ICONS = {
        "filter": "ui-filter-panel button.ant-btn-icon-only",
        "settings": "ui-columns-settings button.ant-btn-icon-only",
        "fullscreen": "ui-fullscreen-table button.ant-btn-icon-only",
    }

    def __init__(self, page: Page):
        super().__init__(page)
        # Специфичные селекторы страницы
        self.header = page.locator("app-notifications-table").first
        self.icons = {
            name: page.locator(selector).first
            for name, selector in self.REQUIRED_ICONS.items()
        }
        self.table = page.locator("table.cdk-table").first

    def navigate_to_notifications(self) -> None:
        """Переход в раздел Уведомления"""
        logger.info(" Навигация: Уведомления")
        self.page.locator('span[nztype="bell"]').first.click(timeout=self.action_timeout)
        self.page.wait_for_load_state("networkidle", timeout=15000)
        expect(self.page).to_have_url(
            re.compile(r".*/notifications"), timeout=self.test_timeout
        )

    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.table).to_be_visible(timeout=30000)
            self.wait_for_table_stable("table.cdk-table")
            logger.info("✅ UI загружен")
            return True
        except Exception as e:
            logger.error(f" Ошибка верификации: {e}")
            self.take_screenshot("verify_initial_fail")
            return False


# =============================================================================
# ТЕСТ
# =============================================================================

def test_notifications_pagination_and_sorting(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
   
    logger.info("🚀 Старт: Пагинация и сортировка → Уведомления")

    # Инициализация Page Object и хелперов
    notifications_page = FinanceNotificationsPage(page)
    pagination = PaginationHelper(page, config=FinanceNotificationsPage.PAGINATION_CONFIG)
    sorting = SortingHelper(
        page,
        sort_config=FinanceNotificationsPage.SORT_CONFIG,
        table_selector="table.cdk-table",
        use_icon_click=True,  # Для ui-sort иконок
        icon_selector_template='th:has-text("{name}") ui-sort'
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info(" Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        notifications_page.navigate_to_notifications()
        take_screenshot("after_nav")

        if not notifications_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")
        soft_assert.check(
            notifications_page.verify_multiple_elements(
                notifications_page.icons, "icons"
            ),
            "Не все иконки отображаются", "ui:icons"
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
        logger.info("🔍 Блок 4: Сортировка (3 колонки)")
        sorting.test_sorting_cycle("id", soft_assert)
        sorting.test_sorting_cycle("date", soft_assert)
        sorting.test_sorting_cycle("theme", soft_assert)

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
