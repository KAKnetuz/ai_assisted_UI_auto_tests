"""
Тест фильтрации раздела Финансы → Платежи.
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


class FinancePaymentsFilterPage(BasePage):
    
    COL_INDICES = {
        "Номер п/п": 5, "ИНН": 7, "КПП": 8, "TIN": 9, "ЛС": 10,
        "Контрагент": 11, "Сумма": 12
    }

    # Кастомные селекторы только для этой страницы
    CUSTOM_FILTER_SELECTORS = {
        "Номер п/п": "th.cdk-column-payment_number",
        "ИНН": "th.cdk-column-client_inn",
        "КПП": "th.cdk-column-client_kpp",
        "TIN": "th.cdk-column-client_tin",
        "ЛС": "th.cdk-column-client_account",
        "Контрагент": "th.cdk-column-contragent_name",
        "Сумма": "th.cdk-column-sum",
        "Дата создания": "th.cdk-column-creation_date",
        "Дата создания п/п": "th.cdk-column-payment_date",
        "Дата исполнения п/п": "th.cdk-column-real_payment_date",
        "Тип платежа": "th.cdk-column-pay_category",
        "Способ оплаты": "th.cdk-column-paid_by_type",
        "Статус платежа": "th.cdk-column-status"
    }

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = page.locator("app-layout").first
        self.tab_payments = page.locator("span.navigations__item:has-text('Платежи')").first

    def navigate_to_payments(self) -> None:
        """Навигация в раздел Платежи"""
        logger.info("📍 Навигация: Финансы → Платежи")
        self.page.locator("a.sidebar__nav-link:has-text('Финансы')").first.click(
            timeout=self.action_timeout
        )
        self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)
        expect(self.page).to_have_url(
            re.compile(r".*/finance/payments"), timeout=self.test_timeout
        )

    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы и наличия данных"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tab_payments).to_be_visible(timeout=self.action_timeout)
            self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)

            try:
                self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=5000)
            except Exception:
                pass

            # Проверяем, что таблица не пуста
            rows = self.page.locator("table.cdk-table tbody tr:visible")
            expect(rows.first).to_be_visible(timeout=self.test_timeout)

            logger.info("✅ UI загружен и содержит данные")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка верификации: {e}")
            self.take_screenshot("verify_initial_fail")
            return False

    def get_col_index(self, col_name: str) -> int:
        return self.COL_INDICES.get(col_name, 1)


# =============================================================================
# ТЕСТ
# =============================================================================

def test_payments_filtering(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    """
    Комплексный тест фильтрации раздела Платежи.
    Проверяет текстовые, чекбоксные, дата-фильтры и частичное совпадение.
    """
    logger.info("🚀 Старт: Фильтрация → Платежи")

    # Инициализация с кастомными селекторами
    payments_page = FinancePaymentsFilterPage(page)
    filter_helper = FilterHelper(
        page,
        table_selector="table.cdk-table",
        custom_selectors=FinancePaymentsFilterPage.CUSTOM_FILTER_SELECTORS
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        payments_page.navigate_to_payments()
        take_screenshot("after_nav")

        if not payments_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ТЕКСТОВЫЕ ФИЛЬТРЫ ====================
        logger.info("🔤 Блок 2: Текстовые фильтры")
        text_cols = ["ИНН", "КПП", "TIN", "ЛС", "Контрагент", "Сумма"]
        NON_EXISTENT_TEXT = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
        NON_EXISTENT_NUMBER = "999999999999999999999999999999999999"

        for col in text_cols:
            location = f"text_filter:{col}"
            col_idx = payments_page.get_col_index(col)
            logger.debug(f"Тестирование колонки: {col}")

            if not filter_helper.open_filter(col):
                soft_assert.check(False, f"Не удалось открыть фильтр для {col}", location)
                continue

            raw_value = filter_helper.get_first_row_cell_text(col_idx)

            if col == "Сумма":
                existing_val = re.sub(r"[^\d]", "", raw_value)
                partial_val = "11" if "11" in existing_val else existing_val[:2] if existing_val else ""
                non_existent = NON_EXISTENT_NUMBER
            else:
                existing_val = raw_value.strip()
                partial_val = existing_val[:3] if len(existing_val) >= 3 else existing_val
                non_existent = NON_EXISTENT_TEXT

            # Поиск по существующему значению
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

            # Поиск по несуществующему значению
            filter_helper.apply_text_filter(non_existent)
            soft_assert.check(
                filter_helper.is_table_empty(),
                f"Таблица не пуста после поиска несуществующего значения",
                f"{location}.non_existent"
            )
            filter_helper.reset_all_filters()

            # Частичное совпадение
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
        checkbox_config = {
            "Тип платежа": ["1C", "Ручное"],
            "Способ оплаты": ["Эквайринг", "Банк"],
            "Статус платежа": ["Успешно", "Ошибка"]
        }

        for col, options in checkbox_config.items():
            location = f"checkbox_filter:{col}"
            logger.debug(f"Тестирование чекбоксов: {col}")

            if not filter_helper.open_filter(col):
                soft_assert.check(False, f"Не удалось открыть фильтр {col}", location)
                continue

            # Одиночный выбор
            filter_helper.apply_checkbox_filter([options[0]])
            soft_assert.check(
                filter_helper.count_table_rows() > 0,
                f"Пусто после выбора '{options[0]}'",
                f"{location}.single"
            )
            filter_helper.reset_all_filters()

            # Множественный выбор
            if filter_helper.open_filter(col):
                filter_helper.apply_checkbox_filter(options)
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    "Пусто после множественного выбора",
                    f"{location}.multiple"
                )
                filter_helper.reset_all_filters()

        # ==================== БЛОК 4: ЧАСТИЧНОЕ СОВПАДЕНИЕ (Номер п/п) ====================
        logger.info("🔢 Блок 4: Частичное совпадение (Номер п/п)")
        location = "partial_match:Номер п/п"

        if filter_helper.open_filter("Номер п/п"):
            full_num = filter_helper.get_first_row_cell_text(5)
            if full_num and len(full_num) > 4:
                filter_helper.apply_text_filter(full_num)
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    "Пусто по полному номеру",
                    f"{location}.full"
                )
                filter_helper.reset_all_filters()

                if filter_helper.open_filter("Номер п/п"):
                    partial = full_num[:3]
                    filter_helper.apply_text_filter(partial)
                    soft_assert.check(
                        filter_helper.count_table_rows() > 0,
                        "Пусто по частичному номеру",
                        f"{location}.partial"
                    )
                    filter_helper.reset_all_filters()
            else:
                logger.warning("Не удалось получить валидный номер п/п")
        else:
            soft_assert.check(False, "Не удалось открыть фильтр Номера п/п", location)

        # ==================== БЛОК 5: ДАТА-ФИЛЬТРЫ ====================
        logger.info("📅 Блок 5: Дата-фильтры")
        date_cols = ["Дата создания", "Дата создания п/п", "Дата исполнения п/п"]
        today = datetime.now()
        past_date = (today - timedelta(days=27)).strftime("%d.%m.%Y")
        current_date = today.strftime("%d.%m.%Y")
        future_start = (today + timedelta(days=90)).strftime("%d.%m.%Y")
        future_end = (today + timedelta(days=97)).strftime("%d.%m.%Y")

        for col in date_cols:
            location = f"date_filter:{col}"
            logger.debug(f"Тестирование дат: {col}")

            # Валидный период
            if not filter_helper.open_filter(col):
                soft_assert.check(False, "Не удалось открыть фильтр дат", location)
                continue

            res = filter_helper.apply_date_filter(past_date, current_date)
            if not res:
                soft_assert.check(False, "Метод apply_date_filter вернул ошибку", f"{location}.valid.method")
            else:
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    f"Таблица пуста для периода {past_date} - {current_date}",
                    f"{location}.valid.data"
                )
            filter_helper.reset_all_filters()

            # Будущий период
            if not filter_helper.open_filter(col):
                continue

            res = filter_helper.apply_date_filter(future_start, future_end)
            if not res:
                soft_assert.check(False, "Ошибка метода для будущих дат", f"{location}.future.method")
            else:
                soft_assert.check(
                    filter_helper.is_table_empty(),
                    f"Таблица НЕ пуста для будущих дат {future_start} - {future_end}",
                    f"{location}.future.data"
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
