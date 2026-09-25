"""
Тест фильтрации раздела Продукты → Продукты.
"""
import re
import logging
from datetime import datetime, timedelta
from playwright.sync_api import Page, expect
from integration_tests.ui.config import Config
from integration_tests.ui.login_page import LoginPage
from integration_tests.ui.base_page import BasePage
from integration_tests.ui.helpers.filter_helper import FilterHelper
from integration_tests.ui.conftest import SoftAssert

logger = logging.getLogger(__name__)


class ProductsFilterPage(BasePage):
    """Page Object для раздела Продукты → Продукты"""

    COL_INDICES = {
        "ID": 1, "Наименование": 2, "Продукт": 3, "Провайдер": 4,
        "Платформа": 5, "Тип": 6, "Статус": 9, "Создан": 10
    }

    def __init__(self, page: Page):
        super().__init__(page)
        # Специфичные селекторы страницы
        self.header = page.locator("app-layout").first
        self.tab_products = page.locator("span.navigations__item:has-text('Продукты')").first

    def navigate_to_products(self) -> None:
        """Навигация в раздел Продукты → Продукты"""
        logger.info("📍 Навигация: Продукты → Продукты")
        self.page.locator("a.sidebar__nav-link:has-text('Продукты')").first.click(
            timeout=self.action_timeout
        )
        self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)

        products_tab = self.page.locator(
            "span.navigations__item:has-text('Продукты'), a:has-text('Продукты')"
        ).first
        if products_tab.count() > 1:
            products_tab.nth(1).click(timeout=self.action_timeout)
        else:
            products_tab.click(timeout=self.action_timeout)

        self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)
        expect(self.page).to_have_url(
            re.compile(r".*/products"), timeout=self.test_timeout
        )

    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tab_products).to_be_visible(timeout=self.action_timeout)
            self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)
            self.wait_for_table_stable("table.cdk-table")
            logger.info("✅ UI загружен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка верификации: {e}")
            self.take_screenshot("verify_initial_fail")
            return False

    def get_col_index(self, col_name: str) -> int:
        """Получает индекс колонки по имени"""
        return self.COL_INDICES.get(col_name, 1)


# =============================================================================
# ТЕСТ
# =============================================================================

def test_products_filtering(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
   
    logger.info("🚀 Старт: Фильтрация → Продукты")

    # Инициализация Page Object и хелпера фильтров
    products_page = ProductsFilterPage(page)
    filter_helper = FilterHelper(page)

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        products_page.navigate_to_products()
        take_screenshot("after_nav")

        if not products_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ТЕКСТОВЫЕ ФИЛЬТРЫ ====================
        logger.info("🔤 Блок 2: Текстовые фильтры")
        text_cols = ["ID", "Наименование", "Продукт", "Провайдер", "Платформа"]
        NON_EXISTENT_TEXT = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"

        for col in text_cols:
            location = f"text_filter:{col}"
            logger.debug(f"Тестирование текстового фильтра: {col}")

            if not filter_helper.open_filter(col):
                soft_assert.check(False, f"Не удалось открыть фильтр для {col}", location)
                continue

            # Получаем существующее значение для поиска
            existing_val = filter_helper.get_first_non_empty_cell_text(
                products_page.get_col_index(col)
            ).strip()
            partial_val = existing_val[:3] if len(existing_val) >= 3 else existing_val

            # Тест 1: Поиск по существующему значению
            if existing_val:
                filter_helper.apply_text_filter(existing_val)
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    f"Таблица пуста после поиска '{existing_val}'",
                    f"{location}.existing"
                )
                filter_helper.reset_all_filters()
                if not filter_helper.open_filter(col):
                    continue

            # Тест 2: Поиск по несуществующему значению
            filter_helper.apply_text_filter(NON_EXISTENT_TEXT)
            soft_assert.check(
                filter_helper.is_table_empty(),
                "Таблица не пуста после поиска несуществующего значения",
                f"{location}.non_existent"
            )
            filter_helper.reset_all_filters()

            # Тест 3: Частичный поиск
            if not filter_helper.open_filter(col):
                continue
            if partial_val and len(partial_val) > 1:
                filter_helper.apply_text_filter(partial_val)
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    f"Таблица пуста после частичного поиска '{partial_val}'",
                    f"{location}.partial"
                )
            filter_helper.reset_all_filters()

        # ==================== БЛОК 3: ЧЕКБОКСНЫЕ ФИЛЬТРЫ ====================
        logger.info("☑️ Блок 3: Чекбоксные фильтры")
        checkbox_cols = {
            "Статус": ["Активен", "Архивный", "Черновик"],
            "Тип": ["Разовая услуга", "Подписной пакет", "Пакет"]
        }

        for col, options in checkbox_cols.items():
            location = f"checkbox_filter:{col}"
            logger.debug(f"Тестирование чекбоксного фильтра: {col}")

            if not filter_helper.open_filter(col):
                soft_assert.check(False, f"Не удалось открыть фильтр {col}", location)
                continue

            # Тест 1: Одиночный выбор
            filter_helper.apply_checkbox_filter([options[0]])
            soft_assert.check(
                filter_helper.count_table_rows() > 0,
                f"Пусто после выбора '{options[0]}'",
                f"{location}.single"
            )
            filter_helper.reset_all_filters()

            # Тест 2: Множественный выбор
            if filter_helper.open_filter(col):
                filter_helper.apply_checkbox_filter(options)
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    "Пусто после множественного выбора",
                    f"{location}.multiple"
                )
                filter_helper.reset_all_filters()

        # ==================== БЛОК 4: ДАТА-ФИЛЬТРЫ ====================
        logger.info("📅 Блок 4: Дата-фильтры")
        today = datetime.now()
        past_date = (today - timedelta(days=28)).strftime("%d.%m.%Y")
        current_date = today.strftime("%d.%m.%Y")
        future_start = (today + timedelta(days=120)).strftime("%d.%m.%Y")
        future_end = (today + timedelta(days=127)).strftime("%d.%m.%Y")

        # Тест 1: Валидный период (прошлое - настоящее)
        if filter_helper.open_filter("Создан"):
            if filter_helper.apply_date_filter(past_date, current_date):
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    f"Таблица пуста для периода {past_date} - {current_date}",
                    "date_filter:Создан.valid"
                )
            filter_helper.reset_all_filters()

        # Тест 2: Будущие даты (должно быть пусто)
        if filter_helper.open_filter("Создан"):
            if filter_helper.apply_date_filter(future_start, future_end):
                current_rows = filter_helper.count_table_rows()
                if current_rows > 0:
                    logger.warning(f"⚠️ Ожидалось 0 строк, найдено {current_rows}")
                    take_screenshot("debug_future_dates_fail")

                soft_assert.check(
                    filter_helper.is_table_empty(),
                    f"Таблица НЕ пуста для будущих дат ({future_start} - {future_end}). Найдено: {current_rows}",
                    "date_filter:Создан.future"
                )
            filter_helper.reset_all_filters()

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
