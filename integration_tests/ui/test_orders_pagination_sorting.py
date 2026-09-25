"""
Комплексный тест раздела Заказы:
  - Проверка UI элементов (иконки, таблица)
  - Проверка структуры таблицы (12 колонок)
  - Пагинация (10/20/50/100 строк, навигация стрелками, переход first/last)
  - Сортировка по 4 колонкам (Внешний номер, Дата создания, Дата реализации, Срок действия до)
"""
import re
import logging
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config
from integration_tests.ui.login_page import LoginPage
from integration_tests.ui.base_page import BasePage
from integration_tests.ui.helpers.pagination_helper import PaginationHelper
from integration_tests.ui.helpers.sorting_helper import SortingHelper
from integration_tests.ui.conftest import SoftAssert

logger = logging.getLogger(__name__)


class FinanceOrdersPage(BasePage):
    """Page Object для раздела Заказы"""

    # =============================================================================
    # КОНФИГУРАЦИЯ КОЛОНОК (12 штук)
    # =============================================================================
    REQUIRED_COLUMNS = [
        "ID", "Внешний номер", "Провайдер", "Покупатель",
        "Наименование услуги", "Сумма", "НДС", "Статус",
        "Статус оплаты", "Дата создания", "Дата реализации", "Срок действия до"
    ]

    COLUMN_SELECTORS = {
        "ID": "th.cdk-column-id",
        "Внешний номер": "th.cdk-column-external_number",
        "Провайдер": "th.cdk-column-seller_name",
        "Покупатель": "th.cdk-column-buyer_name",
        "Наименование услуги": "th.cdk-column-offer_name",
        "Сумма": "th.cdk-column-price",
        "НДС": "th.cdk-column-tax",
        "Статус": "th.cdk-column-status",
        "Статус оплаты": "th.cdk-column-status_pay",
        "Дата создания": "th.cdk-column-date",
        "Дата реализации": "th.cdk-column-realize_date",
        "Срок действия до": "th.cdk-column-offer_valid_until",
    }

    # =============================================================================
    # КОНФИГУРАЦИЯ СОРТИРОВКИ (4 колонки: 1 текст + 3 даты)
    # =============================================================================
    SORT_CONFIG = {
        "external_number": {
            "header_text": "Внешний номер",
            "header_selector": "th.cdk-column-external_number",
            "type": "text"
        },
        "date_created": {
            "header_text": "Дата создания",
            "header_selector": "th.cdk-column-date",
            "type": "date",
            "date_format": "%d.%m.%Y"
        },
        "date_realization": {
            "header_text": "Дата реализации",
            "header_selector": "th.cdk-column-realize_date",
            "type": "date",
            "date_format": "%d.%m.%Y"
        },
        "valid_until": {
            "header_text": "Срок действия до",
            "header_selector": "th.cdk-column-offer_valid_until",
            "type": "date",
            "date_format": "%d.%m.%Y"
        }
    }

    # =============================================================================
    # КОНФИГУРАЦИЯ ПАГИНАЦИИ
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
        "prev_arrow": "li.ant-pagination-prev button",
        "next_arrow": "li.ant-pagination-next button",
        "page_numbers": "li.ant-pagination-item a",
        "first_page": "li.ant-pagination-item[title='1'] a",
        "neutral_click": "app-layout",
    }

    # =============================================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =============================================================================
    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page
        # Специфичные селекторы страницы
        self.header = page.locator("app-layout").first
        self.table = page.locator("table.cdk-table").first
        self.icons = {
            "export": page.locator("app-export button.ant-btn-icon-only").first,
            "filter": page.locator("ui-filter-panel button.ant-btn-icon-only").first,
            "settings": page.locator("ui-columns-settings button.ant-btn-icon-only").first,
            "fullscreen": page.locator("ui-fullscreen-table button.ant-btn-icon-only").first,
        }

    # =============================================================================
    # НАВИГАЦИЯ
    # =============================================================================
    def navigate_to_orders(self) -> None:
        """Переход в раздел Заказы с надежным ожиданием загрузки"""
        logger.info("📍 Навигация: Заказы")

        # Клик по меню
        menu_link = self.page.locator("a.sidebar__nav-link:has-text('Заказы')").first
        expect(menu_link).to_be_visible(timeout=Config.ACTION_TIMEOUT)
        menu_link.click()

        # Ожидание URL и появления таблицы
        expect(self.page).to_have_url(re.compile(r".*/orders"), timeout=Config.TEST_TIMEOUT)

        # Ждем, пока таблица появится в DOM и станет видимой
        expect(self.table).to_be_visible(timeout=Config.TEST_TIMEOUT)

        # Доп. проверка: ждем исчезновения глобальных лоадеров, если они есть
        self._wait_for_table_stability()

    # =============================================================================
    # ПРОВЕРКИ UI
    # =============================================================================
    def verify_initial_state(self) -> bool:
        """Проверка базовой загрузки страницы"""
        try:
            expect(self.header).to_be_visible(timeout=5000)
            expect(self.table).to_be_visible(timeout=10000)

            # Проверяем, что таблица не пуста (есть хотя бы одна строка с данными)
            first_row = self.page.locator("table.cdk-table tbody tr:visible").first
            expect(first_row).to_be_visible(timeout=5000)

            logger.info("✅ UI загружен и содержит данные")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка верификации начального состояния: {e}")
            self.take_screenshot("verify_initial_fail")
            return False

    def verify_table_columns(self) -> list[str]:
        """
        Проверяет наличие всех колонок.
        Возвращает список отсутствующих колонок (пустой список = успех).
        """
        missing_cols = []
        for col_name, selector in self.COLUMN_SELECTORS.items():
            locator = self.page.locator(selector).first
            try:
                # expect автоматически ждет появления элемента
                expect(locator).to_be_visible(timeout=2000)
                logger.debug(f"   ✅ '{col_name}' найдена")
            except (AssertionError, PlaywrightTimeoutError):
                missing_cols.append(col_name)
                logger.warning(f"⚠️ Колонка '{col_name}' не найдена или не видима")

        if missing_cols:
            logger.error(f"⚠️ Отсутствуют колонки: {missing_cols}")
        else:
            logger.info(f"✅ Все {len(self.REQUIRED_COLUMNS)} колонок присутствуют")

        return missing_cols

    def verify_icons_visibility(self) -> list[str]:
        """Проверяет видимость иконок управления"""
        missing_icons = []
        for name, locator in self.icons.items():
            try:
                expect(locator).to_be_visible(timeout=2000)
                logger.debug(f"   ✅ Иконка '{name}' найдена")
            except (AssertionError, PlaywrightTimeoutError):
                missing_icons.append(name)
                logger.warning(f"⚠️ Иконка '{name}' не найдена или не видима")

        if missing_icons:
            logger.error(f"⚠️ Отсутствуют иконки: {missing_icons}")
        else:
            logger.info("✅ Все иконки присутствуют")

        return missing_icons

    def _wait_for_table_stability(self) -> None:
        """Универсальный метод ожидания завершения загрузки/обновления таблицы"""
        # 1. Ждем окончания сетевых запросов 
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            logger.debug("Network not idle, continuing with UI checks")

        # 2. Ждем исчезновения спиннеров
        try:
            self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=5000)
        except PlaywrightTimeoutError:
            logger.debug("No spinner found or spinner didn't disappear")


# =============================================================================
# ТЕСТ
# =============================================================================

def test_orders_pagination_sorting(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    """
    Комплексный тест раздела Заказы:
      1. Авторизация и навигация
      2. Проверка UI (иконки)
      3. Проверка структуры таблицы (12 колонок)
      4. Пагинация (10/20/50/100 строк + навигация)
      5. Сортировка по 4 колонкам (Внешний номер + 3 даты)
    """
    logger.info("🚀 Старт теста: Заказы (Пагинация + Сортировка)")

    # Инициализация Page Object и хелперов
    orders_page = FinanceOrdersPage(page)
    pagination = PaginationHelper(page, config=FinanceOrdersPage.PAGINATION_CONFIG)
    sorting = SortingHelper(
        page,
        sort_config=FinanceOrdersPage.SORT_CONFIG,
        table_selector="table.cdk-table",
        use_icon_click=True,  # Клик по ui-sort иконкам
        icon_selector_template='th:has-text("{name}") ui-sort'
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        orders_page.navigate_to_orders()
        take_screenshot("after_nav")

        if not orders_page.verify_initial_state():
            soft_assert.check(False, "Страница заказов не загрузилась корректно", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")

        missing_icons = orders_page.verify_icons_visibility()
        missing_cols = orders_page.verify_table_columns()

        soft_assert.check(
            len(missing_icons) == 0,
            f"Отсутствуют иконки: {missing_icons}",
            "ui:icons"
        )
        soft_assert.check(
            len(missing_cols) == 0,
            f"Отсутствуют колонки: {missing_cols}",
            "ui:columns"
        )

        # ==================== БЛОК 3: ПАГИНАЦИЯ ====================
        logger.info("📄 Блок 3: Пагинация")

        # Тестируем изменение размера страницы
        page_sizes = [10, 20, 50, 100, 20]  # 20 в конце для проверки возврата

        for count in page_sizes:
            try:
                logger.info(f"   Проверка размера страницы: {count}")
                pagination.change_items_per_page(count)
                orders_page._wait_for_table_stability()

                is_correct = pagination.verify_items_per_page(count)
                soft_assert.check(
                    is_correct,
                    f"Неверное кол-во строк при размере {count}",
                    f"pagination:size_{count}"
                )
            except Exception as e:
                logger.error(f"Ошибка при установке размера {count}: {e}")
                take_screenshot(f"err_pag_size_{count}")
                soft_assert.check(
                    False,
                    f"Исключение при пагинации ({count}): {e}",
                    f"pagination:size_{count}"
                )

        # Тестируем навигацию
        logger.info("🔄 Навигация по страницам")

        try:
            # Вперед на 2 страницы
            if pagination.navigate_pages("next", 2):
                logger.info("   ✅ Навигация вперед успешна")
            else:
                soft_assert.check(False, "Не удалось перейти вперед", "pagination:next")
        except Exception as e:
            logger.error(f"Ошибка навигации вперед: {e}")
            soft_assert.check(False, f"Исключение: {e}", "pagination:next")
            take_screenshot("err_pagination_next")

        try:
            # Назад на 2 страницы
            if pagination.navigate_pages("prev", 2):
                logger.info("   ✅ Навигация назад успешна")
            else:
                soft_assert.check(False, "Не удалось вернуться назад", "pagination:prev")
        except Exception as e:
            logger.error(f"Ошибка навигации назад: {e}")
            soft_assert.check(False, f"Исключение: {e}", "pagination:prev")
            take_screenshot("err_pagination_prev")

        try:
            # Последняя страница
            if pagination.go_to_page("last"):
                logger.info("   ✅ Переход на последнюю страницу успешен")
            else:
                soft_assert.check(False, "Не удалось перейти на последнюю страницу", "pagination:last")
        except Exception as e:
            logger.error(f"Ошибка перехода на последнюю страницу: {e}")
            soft_assert.check(False, f"Исключение: {e}", "pagination:last")
            take_screenshot("err_pagination_last")

        try:
            # Первая страница
            if pagination.go_to_page("first"):
                logger.info("   ✅ Переход на первую страницу успешен")
            else:
                soft_assert.check(False, "Не удалось вернуться на первую страницу", "pagination:first")
        except Exception as e:
            logger.error(f"Ошибка перехода на первую страницу: {e}")
            soft_assert.check(False, f"Исключение: {e}", "pagination:first")
            take_screenshot("err_pagination_first")

        # ==================== БЛОК 4: СОРТИРОВКА ====================
        logger.info("🔍 Блок 4: Сортировка (4 колонки)")

        sort_keys = ["external_number", "date_created", "date_realization", "valid_until"]

        for key in sort_keys:
            try:
                logger.info(f"   Тестирование сортировки: {key}")
                sorting.test_sorting_cycle(key, soft_assert)
                logger.info(f"   ✅ Сортировка {key} успешна")
            except Exception as e:
                logger.error(f"Критическая ошибка сортировки для {key}: {e}")
                take_screenshot(f"err_sort_{key}")
                soft_assert.check(
                    False,
                    f"Исключение сортировки ({key}): {e}",
                    f"sorting:{key}"
                )

        # ==================== ФИНАЛ ====================
        take_screenshot("test_complete")

        if soft_assert.has_errors():
            logger.warning(f"⚠️ Тест завершен с ошибками: {len(soft_assert.errors)}")
        else:
            logger.info("🎉 Тест успешно пройден!")

        soft_assert.report_and_raise_if_failed()

    except AssertionError:
        take_screenshot("test_fail_assertion")
        raise
    except Exception as e:
        logger.error(f"🔥 Неожиданная системная ошибка: {e}", exc_info=True)
        take_screenshot("test_critical_error")
        raise AssertionError(f"Системный сбой теста: {e}") from e
