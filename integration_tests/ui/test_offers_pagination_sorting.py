"""
Тест пагинации и сортировки раздела Продукты → Все предложения.
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


class ProductsAllOffersPage(BasePage):
    """Страница Продукты → Все предложения (только специфичные селекторы)"""

    REQUIRED_COLUMNS = [
        "ID", "Наименование", "Продукт", "Провайдер", "Платформа",
        "Тип", "Цена", "НДС", "Статус", "Создан",
        "Срок действия", "Создано заказов", " "
    ]

    # ИСПРАВЛЕНО: Добавлены type и index для колонок
    SORT_CONFIG = {
        "created": {
            "header_text": "Создан",
            "header_selector": "th.cdk-column-created_date",
            "index": 9,  # 10-я колонка (0-based индекс)
            "type": "date",
            "date_format": "%d.%m.%Y"
        },
        "validity": {
            "header_text": "Срок действия",
            "header_selector": "th.cdk-column-valid_until",
            "index": 10,  # 11-я колонка (0-based индекс)
            "type": "date",
            "date_format": "%d.%m.%Y"
        }
    }

    def __init__(self, page: Page):
        super().__init__(page)
        # Специфичные селекторы страницы
        self.header = page.locator("app-layout").first
        self.tabs = {
            "all_offers": page.locator("span.navigations__item:has-text('Все предложения')").first,
            "products": page.locator("span.navigations__item:has-text('Продукты')").first
        }
        self.icons = {
            "filter": page.locator("ui-filter-panel button.ant-btn-icon-only").first,
            "settings": page.locator("ui-columns-settings button.ant-btn-icon-only").first,
            "fullscreen": page.locator("ui-fullscreen-table button.ant-btn-icon-only").first
        }
        self.table = page.locator("app-all-offers-table table.cdk-table").first

    def navigate_to_all_offers(self) -> None:
        """Навигация в раздел Все предложения"""
        logger.info("📍 Навигация: Продукты → Все предложения")
        self.page.locator("a.sidebar__nav-link:has-text('Продукты')").first.click(
            timeout=self.action_timeout
        )
        expect(self.tabs["all_offers"]).to_be_visible(timeout=self.test_timeout)
        self.click_if_not_active(self.tabs["all_offers"], "active-route")
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page).to_have_url(
            re.compile(r".*/products/offer-list"), timeout=self.test_timeout
        )

    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tabs["all_offers"]).to_be_visible(timeout=self.action_timeout)
            expect(self.table).to_be_visible(timeout=30000)
            self.wait_for_table_stable("table.cdk-table")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка верификации: {e}")
            self.take_screenshot("verify_initial_fail")
            return False


# =============================================================================
# ТЕСТ
# =============================================================================

def test_all_offers_pagination_and_sorting(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    """
    Комплексный тест пагинации и сортировки раздела Все предложения.
    Использует:
      - SoftAssert для накопления ошибок
      - PaginationHelper для переиспользуемой логики пагинации
      - SortingHelper для переиспользуемой логики сортировки
    """
    logger.info("🚀 Старт: Пагинация и сортировка → Все предложения")

    # Инициализация Page Object и хелперов
    offers_page = ProductsAllOffersPage(page)
    pagination = PaginationHelper(page)
    sorting = SortingHelper(page, ProductsAllOffersPage.SORT_CONFIG)

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        offers_page.navigate_to_all_offers()
        take_screenshot("after_nav")

        if not offers_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")
        soft_assert.check(
            offers_page.verify_multiple_elements(offers_page.tabs, "tabs"),
            "Вкладки не отображаются", "ui:tabs"
        )
        soft_assert.check(
            offers_page.verify_multiple_elements(offers_page.icons, "icons"),
            "Не все иконки отображаются", "ui:icons"
        )
        soft_assert.check(
            offers_page.verify_table_columns(ProductsAllOffersPage.REQUIRED_COLUMNS),
            "Отсутствуют колонки", "ui:columns"
        )

        # ==================== БЛОК 3: ПАГИНАЦИЯ ====================
        logger.info("📄 Блок 3: Пагинация")
        for count in [10, 50, 100, 20]:
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
        logger.info("🔍 Блок 4: Сортировка")
        sorting.test_sorting_cycle("created", soft_assert)
        sorting.test_sorting_cycle("validity", soft_assert)

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