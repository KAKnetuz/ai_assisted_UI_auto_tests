"""
Комплексный тест раздела Заказы - Фильтрация:
  - Проверка UI элементов (иконки, таблица, колонки)
  - Текстовые фильтры (ID, Провайдер, Покупатель, Наименование услуги)
  - Внешний номер — отдельная логика (уникальный идентификатор)
  - Чекбоксные фильтры (Статус, Статус оплаты)
  - Дата-фильтры (Дата создания, Дата реализации, Срок действия до)
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


class FinanceOrdersPage(BasePage):
    """Page Object для раздела Заказы с функционалом фильтрации"""

    # =============================================================================
    # КОНФИГУРАЦИЯ КОЛОНОК (12 штук)
    # =============================================================================
    REQUIRED_COLUMNS = [
        "ID", "Внешний номер", "Провайдер", "Покупатель",
        "Наименование услуги", "Сумма", "НДС", "Статус",
        "Статус оплаты", "Дата создания", "Дата реализации", "Срок действия до"
    ]

    # Селекторы колонок для фильтров
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

    # Индексы колонок для извлечения данных
    COL_INDICES = {
        "ID": 1,
        "Внешний номер": 2,
        "Провайдер": 3,
        "Покупатель": 4,
        "Наименование услуги": 5,
        "Сумма": 6,
        "НДС": 7,
        "Статус": 8,
        "Статус оплаты": 9,
        "Дата создания": 10,
        "Дата реализации": 11,
        "Срок действия до": 12,
    }

    # =============================================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =============================================================================
    def __init__(self, page: Page):
        super().__init__(page)
        # Специфичные селекторы страницы
        self.header = page.locator("app-layout").first
        self.table = page.locator("table.cdk-table").first
        self.tab_orders = page.locator("span.navigations__item:has-text('Заказы')").first
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
        """Переход в раздел Заказы"""
        logger.info("📍 Навигация: Заказы")
        self.page.locator("a.sidebar__nav-link:has-text('Заказы')").first.click(
            timeout=self.action_timeout
        )
        expect(self.page).to_have_url(
            re.compile(r".*/orders"), timeout=self.test_timeout
        )
        expect(self.table).to_be_visible(timeout=self.test_timeout)

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

    def verify_table_columns(self) -> bool:
        """
        Проверяет наличие всех 12 колонок таблицы.
        """
        logger.info("🔍 Проверка 12 колонок таблицы...")
        missing = []

        for col_name, selector in self.COLUMN_SELECTORS.items():
            locator = self.page.locator(selector).first
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

    def get_col_index(self, col_name: str) -> int:
        """Получает индекс колонки по имени"""
        return self.COL_INDICES.get(col_name, 1)


# =============================================================================
# ТЕСТ
# =============================================================================

def test_orders_filtering(
    page: Page,
    soft_assert: SoftAssert,
    take_screenshot
) -> None:
    
    logger.info("🚀 Старт: Фильтрация → Заказы")

    # Инициализация Page Object и хелпера фильтров
    orders_page = FinanceOrdersPage(page)
    filter_helper = FilterHelper(
        page,
        table_selector="table.cdk-table",
        custom_selectors=FinanceOrdersPage.COLUMN_SELECTORS
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        orders_page.navigate_to_orders()
        take_screenshot("after_nav")

        if not orders_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ПРОВЕРКА UI ====================
        logger.info("🖥 Блок 2: Проверка UI элементов")
        soft_assert.check(
            orders_page.verify_multiple_elements(orders_page.icons, "icons"),
            "Не все иконки отображаются", "ui:icons"
        )
        soft_assert.check(
            orders_page.verify_table_columns(),
            "Не все 12 колонок таблицы найдены", "ui:columns"
        )

        # ==================== БЛОК 3: ТЕКСТОВЫЕ ФИЛЬТРЫ ====================
        logger.info("🔤 Блок 3: Текстовые фильтры")

        # Текстовые колонки 
        text_cols = ["ID", "Провайдер", "Покупатель", "Наименование услуги"]
        NON_EXISTENT_TEXT = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
        NON_EXISTENT_NUMBER = "999999999999999"

        for col in text_cols:
            location = f"text_filter:{col}"
            col_idx = orders_page.get_col_index(col)
            logger.debug(f"Тестирование колонки: {col}")

            if not filter_helper.open_filter(col):
                soft_assert.check(False, f"Не удалось открыть фильтр для {col}", location)
                continue

            # Получаем значение из первой строки
            raw_value = filter_helper.get_first_row_cell_text(col_idx)

            # Если данных в колонке нет — пропускаем
            if not raw_value:
                logger.warning(f"⚠️ Пропуск колонки {col}: нет данных для фильтрации")
                filter_helper.reset_all_filters()
                continue

            # Формируем тестовые данные
            if col == "ID":
                existing_val = re.sub(r"[^\d]", "", raw_value)
                partial_val = existing_val[:3] if len(existing_val) >= 3 else existing_val[:2] if existing_val else ""
                non_existent = NON_EXISTENT_NUMBER
            else:
                existing_val = raw_value.strip()
                partial_val = existing_val[:3] if len(existing_val) >= 3 else existing_val
                non_existent = NON_EXISTENT_TEXT

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
            filter_helper.apply_text_filter(non_existent)
            soft_assert.check(
                filter_helper.is_table_empty(),
                f"Таблица не пуста после поиска несуществующего значения",
                f"{location}.non_existent"
            )
            filter_helper.reset_all_filters()

            # Тест 3: Частичное совпадение
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

        # ==================== БЛОК 3.1: ВНЕШНИЙ НОМЕР  ====================
        logger.info("🔢 Блок 3.1: Фильтр 'Внешний номер' (уникальный идентификатор)")
        location = "text_filter:Внешний номер"
        col_idx = orders_page.get_col_index("Внешний номер")

        if filter_helper.open_filter("Внешний номер"):
            # Получаем полный внешний номер из первой строки
            full_external_number = filter_helper.get_first_row_cell_text(col_idx).strip()

            if not full_external_number:
                logger.warning("⚠️ Пропуск 'Внешний номер': нет данных")
                filter_helper.reset_all_filters()
            else:
                logger.info(f"📋 Найден внешний номер: '{full_external_number}'")

                # Тест 1: Полное совпадение — должна быть ровно 1 запись (или несколько, если есть дубликаты)
                filter_helper.apply_text_filter(full_external_number)
                row_count = filter_helper.count_table_rows()
                soft_assert.check(
                    row_count > 0,
                    f"Таблица пуста после поиска полного внешнего номера '{full_external_number}'",
                    f"{location}.full_match"
                )
                # Дополнительно проверяем, что найдено не слишком много записей (уникальный идентификатор)
                if row_count > 0:
                    logger.info(f"✅ Найдено записей по полному совпадению: {row_count}")
                    # Для уникального идентификатора ожидаем 1-5 записей (не больше)
                    soft_assert.check(
                        row_count <= 5,
                        f"Слишком много записей ({row_count}) для уникального внешнего номера '{full_external_number}'",
                        f"{location}.full_match.unique"
                    )
                filter_helper.reset_all_filters()

                # Тест 2: Частичное совпадение по УНИКАЛЬНОЙ части (последние 4-5 символов)
                # Например, для "V-2026-54321" берём "54321"
                if len(full_external_number) >= 5:
                    # Берём последние 5 символов (уникальная часть)
                    unique_part = full_external_number[-5:]
                    logger.debug(f"   Тест частичного совпадения по уникальной части: '{unique_part}'")

                    if filter_helper.open_filter("Внешний номер"):
                        filter_helper.apply_text_filter(unique_part)
                        partial_count = filter_helper.count_table_rows()
                        soft_assert.check(
                            partial_count > 0,
                            f"Таблица пуста после частичного поиска '{unique_part}'",
                            f"{location}.partial_unique"
                        )
                        logger.info(f"✅ Найдено записей по частичному совпадению '{unique_part}': {partial_count}")
                        filter_helper.reset_all_filters()

                # Тест 3: Несуществующее значение
                if filter_helper.open_filter("Внешний номер"):
                    filter_helper.apply_text_filter(NON_EXISTENT_TEXT)
                    soft_assert.check(
                        filter_helper.is_table_empty(),
                        f"Таблица не пуста после поиска несуществующего внешнего номера",
                        f"{location}.non_existent"
                    )
                    filter_helper.reset_all_filters()
        else:
            soft_assert.check(False, "Не удалось открыть фильтр 'Внешний номер'", location)

        # ==================== БЛОК 4: ЧЕКБОКСНЫЕ ФИЛЬТРЫ ====================
        logger.info("☑️ Блок 4: Чекбоксные фильтры")
        checkbox_config = {
            "Статус": ["Новый", "Отменён", "Использован"],
            "Статус оплаты": ["Оплачен", "Не оплачен", "Не требует"]
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

        # ==================== БЛОК 5: ДАТА-ФИЛЬТРЫ ====================
        logger.info("📅 Блок 5: Дата-фильтры")
        date_cols = ["Дата создания", "Дата реализации", "Срок действия до"]
        today = datetime.now()
        past_date = (today - timedelta(days=30)).strftime("%d.%m.%Y")
        current_date = today.strftime("%d.%m.%Y")
        future_start = (today + timedelta(days=90)).strftime("%d.%m.%Y")
        future_end = (today + timedelta(days=120)).strftime("%d.%m.%Y")

        for col in date_cols:
            location = f"date_filter:{col}"
            logger.debug(f"Тестирование дат: {col}")

            # Валидный период
            if not filter_helper.open_filter(col):
                soft_assert.check(False, f"Не удалось открыть фильтр дат {col}", location)
                continue

            res = filter_helper.apply_date_filter(past_date, current_date)
            if not res:
                soft_assert.check(False, f"Метод apply_date_filter вернул ошибку", f"{location}.valid.method")
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
                soft_assert.check(False, f"Ошибка метода для будущих дат", f"{location}.future.method")
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
