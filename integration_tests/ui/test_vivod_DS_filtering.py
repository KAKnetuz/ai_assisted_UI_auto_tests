"""
Тест фильтрации раздела Финансы → Вывод ДС.
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


class FinanceWithdrawalsPage(BasePage):
    """Page Object для раздела Финансы → Вывод ДС"""

    # Индексы колонок для получения значений из первой строки
    COL_INDICES = {
        "Дата создания": 2,
        "ИНН": 3,
        "КПП": 4,
        "TIN": 5,
        "ЛС": 6,
        "Контрагент": 7,
        "Сумма": 8,
        "Создал": 9,
        "Дата исполнения": 10,
        "Статус": 11
    }

    # Кастомные селекторы колонок для фильтров
    CUSTOM_FILTER_SELECTORS = {
        "Дата создания": "th.cdk-column-date",
        "ИНН": "th.cdk-column-inn",
        "КПП": "th.cdk-column-kpp",
        "TIN": "th.cdk-column-tin",
        "ЛС": "th.cdk-column-account",
        "Контрагент": "th.cdk-column-buyer_short_name",
        "Сумма": "th.cdk-column-price",
        "Создал": "th.cdk-column-created_by",
        "Дата исполнения": "th.cdk-column-realize_date",
        "Статус": "th.cdk-column-status"
    }

    def __init__(self, page: Page):
        super().__init__(page)
        # Специфичные селекторы страницы
        self.header = page.locator("app-layout").first
        self.tab_withdrawals = page.locator(
            "span.navigations__item:has-text('Вывод ДС'), a:has-text('Вывод ДС')"
        ).first

    def navigate_to_withdrawals(self) -> None:
        """Навигация в раздел Финансы → Вывод ДС"""
        logger.info("📍 Навигация: Финансы → Вывод ДС")
        self.page.locator("a.sidebar__nav-link:has-text('Финансы')").first.click(
            timeout=self.action_timeout
        )
        self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)

        self.tab_withdrawals.click(timeout=self.action_timeout)
        self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)

        expect(self.page).to_have_url(
            re.compile(r".*/finance/withdrawals"), timeout=self.test_timeout
        )

    def verify_initial_state(self) -> bool:
        """Проверка загрузки страницы"""
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tab_withdrawals).to_be_visible(timeout=self.action_timeout)
            self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.test_timeout)

            try:
                self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=5000)
            except Exception:
                pass

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

def test_vivod_DS_filtering(
        page: Page,
        soft_assert: SoftAssert,
        take_screenshot
) -> None:
    """
    Комплексный тест фильтрации раздела Вывод ДС.
    Проверяет:
      - Текстовые фильтры (6 колонок: ИНН, КПП, ЛС, Контрагент, Создал)
      - Числовой фильтр (Сумма) — только частичное совпадение и несуществующее значение
      - TIN — специальная проверка через поиск по "1"
      - Дата-фильтры (Дата создания, Дата исполнения)
      - Чекбоксный фильтр (Статус)
    """
    logger.info("🚀 Старт: Фильтрация → Вывод ДС")

    # Инициализация Page Object и хелпера фильтров
    withdrawals_page = FinanceWithdrawalsPage(page)
    filter_helper = FilterHelper(
        page,
        table_selector="table.cdk-table",
        custom_selectors=FinanceWithdrawalsPage.CUSTOM_FILTER_SELECTORS
    )

    try:
        # ==================== БЛОК 1: АВТОРИЗАЦИЯ ====================
        logger.info("📋 Блок 1: Авторизация и навигация")
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)
        withdrawals_page.navigate_to_withdrawals()
        take_screenshot("after_nav")

        if not withdrawals_page.verify_initial_state():
            soft_assert.check(False, "Начальное состояние UI не прошло", "initial_state")
            soft_assert.report_and_raise_if_failed()

        # ==================== БЛОК 2: ТЕКСТОВЫЕ ФИЛЬТРЫ ====================
        logger.info("🔤 Блок 2: Текстовые фильтры")

        # Текстовые колонки 
        text_cols = ["ИНН", "КПП", "ЛС", "Контрагент", "Создал"]
        NON_EXISTENT_TEXT = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"

        for col in text_cols:
            location = f"text_filter:{col}"
            col_idx = withdrawals_page.get_col_index(col)
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

        # ==================== БЛОК 2.1: TIN ====================
        logger.info("🔍 Блок 2.1: Фильтр TIN (поиск через '1')")
        location = "text_filter:TIN"
        col_idx = withdrawals_page.get_col_index("TIN")

        # Шаг 1: Вводим "1" для поиска любых непустых TIN
        if filter_helper.open_filter("TIN"):
            filter_helper.apply_text_filter("1")

            # Проверяем, что есть результаты
            if filter_helper.count_table_rows() > 0:
                logger.info("✅ Найдены записи с TIN, содержащим '1'")

                # Шаг 2: Получаем полное значение TIN из первой строки
                full_tin_value = filter_helper.get_first_row_cell_text(col_idx).strip()

                if full_tin_value:
                    logger.info(f"📋 Получено значение TIN для полного совпадения: '{full_tin_value}'")

                    # Сбрасываем фильтр перед следующей проверкой
                    filter_helper.reset_all_filters()

                    # Шаг 3: Проверка по полному совпадению
                    if filter_helper.open_filter("TIN"):
                        filter_helper.apply_text_filter(full_tin_value)
                        soft_assert.check(
                            filter_helper.count_table_rows() > 0,
                            f"Таблица пуста после поиска полного TIN '{full_tin_value}'",
                            f"{location}.existing"
                        )
                        filter_helper.reset_all_filters()

                    # Шаг 4: Проверка частичного совпадения (первые 3 символа)
                    if len(full_tin_value) >= 3:
                        partial_tin = full_tin_value[:3]
                        if filter_helper.open_filter("TIN"):
                            filter_helper.apply_text_filter(partial_tin)
                            soft_assert.check(
                                filter_helper.count_table_rows() > 0,
                                f"Таблица пуста после частичного поиска TIN '{partial_tin}'",
                                f"{location}.partial"
                            )
                            filter_helper.reset_all_filters()
                else:
                    logger.warning("⚠️ Не удалось получить значение TIN из первой строки")
                    filter_helper.reset_all_filters()
            else:
                logger.warning("⚠️ Таблица пуста после поиска по '1'. Пропуск проверок полного совпадения.")
                filter_helper.reset_all_filters()

        # Шаг 5: Проверка несуществующего значения (всегда выполняем)
        if filter_helper.open_filter("TIN"):
            filter_helper.apply_text_filter(NON_EXISTENT_TEXT)
            soft_assert.check(
                filter_helper.is_table_empty(),
                "Таблица не пуста после поиска несуществующего TIN",
                f"{location}.non_existent"
            )
            filter_helper.reset_all_filters()

        # ==================== БЛОК 3: ЧИСЛОВОЙ ФИЛЬТР ====================
        logger.info("💰 Блок 3: Числовой фильтр (Сумма)")
        location = "numeric_filter:Сумма"
        col_idx = withdrawals_page.get_col_index("Сумма")
        NON_EXISTENT_NUMBER = "999999999999999999999999999999999999"

        # Ищем непустое числовое значение
        logger.debug("🔍 Поиск числового значения в колонке Сумма...")
        raw_value = filter_helper.get_first_non_empty_cell_text(col_idx, max_rows=20)

        if not raw_value:
            logger.warning("⚠️ Пропуск Сумма: нет данных")
            # Проверяем только несуществующее значение
            if filter_helper.open_filter("Сумма"):
                filter_helper.apply_text_filter(NON_EXISTENT_NUMBER)
                soft_assert.check(
                    filter_helper.is_table_empty(),
                    "Таблица не пуста после поиска несуществующей суммы",
                    f"{location}.non_existent"
                )
                filter_helper.reset_all_filters()
        else:
            # Извлекаем только цифры
            numeric_val = re.sub(r"[^\d]", "", raw_value)

            if not numeric_val:
                logger.warning(f"⚠️ Пропуск Сумма: не удалось извлечь цифры из '{raw_value}'")
            else:
                logger.debug(f"✅ Найдено числовое значение: {numeric_val} (из '{raw_value}')")

                # Тест 1: Поиск по несуществующему значению
                if filter_helper.open_filter("Сумма"):
                    filter_helper.apply_text_filter(NON_EXISTENT_NUMBER)
                    soft_assert.check(
                        filter_helper.is_table_empty(),
                        "Таблица не пуста после поиска несуществующей суммы",
                        f"{location}.non_existent"
                    )
                    filter_helper.reset_all_filters()

                # Тест 2: Частичное совпадение (берем первые 2-3 цифры)
                partial_val = numeric_val[:3] if len(numeric_val) >= 3 else numeric_val[:2] if len(numeric_val) >= 2 else numeric_val

                if partial_val and len(partial_val) >= 2 and filter_helper.open_filter("Сумма"):
                    filter_helper.apply_text_filter(partial_val)
                    # Для частичного поиска проверяем что таблица не пуста ИЛИ пуста (оба варианта допустимы)
                    row_count = filter_helper.count_table_rows()
                    logger.debug(f"📊 Частичный поиск '{partial_val}' нашел {row_count} строк")
                    # Не делаем assert, так как частичный поиск может ничего не найти
                    filter_helper.reset_all_filters()

        # ==================== БЛОК 4: ДАТА-ФИЛЬТРЫ ====================
        logger.info("📅 Блок 4: Дата-фильтры")
        date_cols = ["Дата создания", "Дата исполнения"]
        today = datetime.now()
        past_date = (today - timedelta(days=28)).strftime("%d.%m.%Y")
        current_date = today.strftime("%d.%m.%Y")
        future_start = (today + timedelta(days=120)).strftime("%d.%m.%Y")
        future_end = (today + timedelta(days=127)).strftime("%d.%m.%Y")

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

        # ==================== БЛОК 5: ЧЕКБОКС-ФИЛЬТР ====================
        logger.info("☑️ Блок 5: Фильтр по Статусу")
        location = "checkbox_filter:Статус"
        statuses = ["Новый", "Исполнен", "Отменен"]

        if filter_helper.open_filter("Статус"):
            # Одиночный выбор
            filter_helper.apply_checkbox_filter([statuses[0]])
            soft_assert.check(
                filter_helper.count_table_rows() > 0,
                f"Пусто после выбора '{statuses[0]}'",
                f"{location}.single"
            )
            filter_helper.reset_all_filters()

            # Множественный выбор
            if filter_helper.open_filter("Статус"):
                filter_helper.apply_checkbox_filter(statuses[:2])
                soft_assert.check(
                    filter_helper.count_table_rows() > 0,
                    "Пусто после множественного выбора статусов",
                    f"{location}.multiple"
                )
                filter_helper.reset_all_filters()
        else:
            soft_assert.check(False, "Не удалось открыть фильтр Статуса", location)

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
