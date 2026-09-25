"""
Комплексный тест раздела Скидки:
  - Проверка UI элементов (header, иконки, кнопка создания)
  - Проверка структуры таблицы (10 колонок)
  - Пагинация (10/20/50/100 строк, навигация стрелками, переход first/last)
  - Сортировка по 2 датам (Активна с, Активна по)
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


class FinanceDiscountsPage(BasePage):
    """Page Object для раздела Скидки"""

    # =============================================================================
    # КОНФИГУРАЦИЯ КОЛОНОК (10 штук)
    # =============================================================================
    REQUIRED_COLUMNS = [
        "No.", "Наименование", "Размер", "Статус",
        "Активна с", "Активна по", "Доступно использова",
        "Создал", "Промокод", "Персональная"
    ]

    # =============================================================================
    # КОНФИГУРАЦИЯ СОРТИРОВКИ (2 колонки с датами)
    # =============================================================================
    SORT_CONFIG = {
        "valid_from": {
            "header_text": "Активна с",
            "header_selector": "th.cdk-column-valid_from",
            "index": 4,
            "type": "date",
            "date_format": "%d.%m.%Y"
        },
        "valid_until": {
            "header_text": "Активна по",
            "header_selector": "th.cdk-column-valid_until",
            "index": 5,
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
        self.header = page.locator("a.sidebar__nav-link.active span.sidebar__text:has-text('Скидки')").first
        self.create_button = page.locator("button.ant-btn.button.ant-btn-primary.ant-btn-icon-only").first
        self.icons = {
            "filter": page.locator("ui-filter-panel button.ant-btn-icon-only").first,
            "settings": page.locator("ui-columns-settings button.ant-btn-icon-only").first,
            "fullscreen": page.locator("ui-fullscreen-table button.ant-btn-icon-only").first,
        }
        self.table = page.locator("app-discount-table table.cdk-table").first

    # =============================================================================
    # НАВИГАЦИЯ
    # =============================================================================
    def navigate_to_discounts(self) -> None:
        logger.info("📍 Навигация: Скидки")
        self.page.locator(
            "a.sidebar__nav-link:has-text('Скидки'), li.sidebar__nav-item:has-text('Скидки') a"
        ).first.click(timeout=self.action_timeout)

        self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)
        expect(self.page).to_have_url(
            re.compile(r".*/discounts"), timeout=self.test_timeout
        )

    # =============================================================================
    # ПРОВЕРКИ UI
    # =============================================================================
    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы и наличия данных"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
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

    def verify_create_button(self) -> bool:
        """Проверяет отображение кнопки создания скидки"""
        try:
            expect(self.create_button).to_be_visible(timeout=self.action_timeout)
            logger.debug("✅ Кнопка создания отображается")
            return True
        except Exception as e:
            logger.error(f"❌ Кнопка создания не найдена: {e}")
            return False

    def verify_table_columns(self) -> bool:
        """
        Проверяет наличие всех 10 колонок таблицы.
        """
        logger.info("🔍 Проверка 10 колонок таблицы...")
        missing = []

        for col_name in self.REQUIRED_COLUMNS:
            # Используем contains-поиск вместо exact match для обрезанных заголовков
            locator = self.page.locator(f"th:has-text('{col_name}')").first
            try:
                if locator.is_visible(timeout=1000):
                    logger.debug(f"   ✅ '{col_name}' найдена")
                else:
                    missing.append(col_name)
                    logger.error(f"   ❌ '{col_name}' НЕ найдена")
            except Exception:
                missing.append(col_name)

        if missing:
            logger.error(f"⚠️ Отсутствуют колонки: {missing}")
            return False

        logger.info(f"✅ Все {len(self.REQUIRED_COLUMNS)} колонок присутствуют")
        return True


# =============================================================================
# ТЕСТ
# =============================================================================

def test_skidki_pagination_sorting(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    """
    Комплексный тест раздела Скидки:
      1. Авторизация и навигация
      2. Проверка UI (header, иконки, кнопка создания)
      3. Проверка структуры таблицы (10 колонок)
      4. Пагинация (10/20/50/100 строк + навигация)
      5. Сортировка по 2 датам (Активна с, Активна по)
    """
    logger.info("🚀 Старт: Пагинация и сортировка → Скидки")

    # Инициализация Page Object и хелперов
    discounts_page = FinanceDiscountsPage(page)
    pagination = PaginationHelper(page, config=FinanceDiscountsPage.PAGINATION_CONFIG)
    sorting = SortingHelper(
        page,
        sort_config=FinanceDiscountsPage.SORT_CONFIG,
        table_selector="table.cdk-table",
        use_icon_click=True,  
        icon_selector_template='th:has-text("{name}") ui-sort'
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        discounts_page.navigate_to_discounts()
        take_screenshot("after_nav")

        if not discounts_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")
        soft_assert.check(
            discounts_page.verify_multiple_elements(discounts_page.icons, "icons"),
            "Не все иконки отображаются", "ui:icons"
        )
        soft_assert.check(
            discounts_page.verify_create_button(),
            "Кнопка создания не отображается", "ui:create_btn"
        )
        soft_assert.check(
            discounts_page.verify_table_columns(),
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
        logger.info("🔍 Блок 4: Сортировка (2 колонки с датами)")
        sorting.test_sorting_cycle("valid_from", soft_assert)
        sorting.test_sorting_cycle("valid_until", soft_assert)

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
