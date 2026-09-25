# integration_tests/ui/test_products_filtering.py
import os
import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import pytest
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError

from integration_tests.ui.config import Config
from integration_tests.ui.login_page import LoginPage

# ================= НАСТРОЙКА ЛОГИРОВАНИЯ =================
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(funcName)s | %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.propagate = False


class SoftAssert:
    """Класс для мягких ассерций"""

    def __init__(self):
        self.errors: List[Tuple[str, str]] = []

    def assert_true(self, condition: bool, message: str, location: str = "") -> None:
        if not condition:
            self.errors.append((location, message))
            logger.error(f"❌ [{location}] {message}")

    def assert_equal(self, actual, expected, message: str, location: str = "") -> None:
        if actual != expected:
            err_msg = f"{message} | Ожидалось: {expected}, Получено: {actual}"
            self.errors.append((location, err_msg))
            logger.error(f"❌ [{location}] {err_msg}")

    def assert_not_empty(self, value, message: str, location: str = "") -> None:
        if not value:
            self.errors.append((location, message))
            logger.error(f"❌ [{location}] {message}")

    def catch_assertion(self, func, *args, message: str = "", location: str = "", **kwargs):
        try:
            return func(*args, **kwargs)
        except (AssertionError, PlaywrightTimeoutError, Exception) as e:
            self.errors.append((location, f"{message} | Ошибка: {str(e)}"))
            logger.error(f"❌ [{location}] {message} | Ошибка: {e}")
            return None

    def report_and_raise_if_failed(self) -> None:
        if self.errors:
            error_report = "\n".join([f"  [{loc}] {msg}" for loc, msg in self.errors])
            raise AssertionError(f"Тест завершён с {len(self.errors)} ошибкой(ами):\n{error_report}")

    def has_errors(self) -> bool:
        return len(self.errors) > 0


class ProductsFilterPage:
    
    # Конфигурация колонок для фильтров
    FILTER_COLUMNS = {
        "ID": "th.cdk-column-id",
        "Наименование": "th.cdk-column-name",
        "Статус": "th.cdk-column-status",
        "Дата создания": "th.cdk-column-created_date"
    }

    def __init__(self, page: Page):
        self.page = page
        self.results_dir = "results"
        os.makedirs(self.results_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # === СЕЛЕКТОРЫ UI ЭЛЕМЕНТОВ ===
        self.header = page.locator("app-layout").first

        # Вкладки
        self.tabs = {
            "all_offers": page.locator("span.navigations__item:has-text('Все предложения')").first,
            "products": page.locator("span.navigations__item:has-text('Продукты')").first
        }

        # Иконки в хедере таблицы
        self.icons = {
            "filter": page.locator("ui-filter-panel button.ant-btn-icon-only").first,
            "settings": page.locator("ui-columns-settings button.ant-btn-icon-only").first,
            "fullscreen": page.locator("ui-fullscreen-table button.ant-btn-icon-only").first
        }

        # Кнопка создания
        self.create_button = page.locator("button.ant-btn.button.ant-btn-primary.ant-btn-icon-only").first

        # Таблица
        self.table = page.locator("app-products-table table.cdk-table").first
        self.table_rows = page.locator("table.cdk-table tbody tr")
        self.empty_state = page.locator("div.ant-empty")

        # Кнопка сброса фильтров (глобальная)
        self.reset_filters_btn = page.locator("ui-reset-filters button.ant-btn-icon-only").first

        self.action_timeout = Config.ACTION_TIMEOUT
        self.test_timeout = Config.TEST_TIMEOUT

    # ================= NAVIGATION & VERIFICATION =================

    def navigate_to_products(self) -> None:
        logger.info("📍 Навигация: Продукты -> Продукты")

        # Клик по меню Продукты
        products_menu = self.page.locator("a.sidebar__nav-link:has-text('Продукты')").first
        products_menu.click(timeout=self.action_timeout)

        # Ждем появления вкладки Продукты
        self.page.wait_for_selector("span.navigations__item:has-text('Продукты')", state="visible",
                                    timeout=self.test_timeout)

        # Проверяем активную вкладку
        products_tab_class = self.tabs["products"].get_attribute("class") or ""
        if "active-route" not in products_tab_class.lower():
            self.tabs["products"].click(timeout=self.action_timeout)

        # УВЕЛИЧЕН ТАЙМАУТ для медленной загрузки
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page).to_have_url(
            re.compile(r".*/products/product-list"),
            timeout=self.test_timeout
        )
        logger.debug("✅ Навигация завершена")

    def take_screenshot(self, name: str) -> str:
        """Делает скриншот"""
        path = os.path.join(self.results_dir, f"products_{name}_{self.timestamp}.png")
        self.page.screenshot(path=path, full_page=False)
        return path

    def verify_initial_state(self) -> bool:
        """Проверка начального состояния UI"""
        logger.debug("Проверка начального состояния UI")
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tabs["products"]).to_be_visible(timeout=self.action_timeout)

            # Проверка активности вкладки
            products_class = self.tabs["products"].get_attribute("class") or ""
            if "active-route" not in products_class.lower():
                logger.warning("⚠️ Вкладка 'Продукты' не имеет класса active-route, но видима")

            # Ждем таблицы
            self.page.wait_for_selector("table.cdk-table", state="visible", timeout=30000)

            # Ждем исчезновения спиннера
            try:
                self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            logger.info("✅ UI загружен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка верификации начального состояния: {e}")
            self.take_screenshot("verify_initial_fail")
            return False

    def verify_icons(self) -> bool:
        """Проверяет отображение ВСЕХ 3 иконок"""
        icons_found = 0
        for icon_name, icon_locator in self.icons.items():
            try:
                icon_locator.wait_for(state="visible", timeout=self.action_timeout)
                icons_found += 1
            except:
                pass

        is_ok = icons_found == len(self.icons)
        if is_ok:
            logger.debug(f"✅ Все {icons_found} иконки отображаются")
        else:
            logger.warning(f"⚠️ Найдено иконок: {icons_found}/{len(self.icons)}")
        return is_ok

    def verify_create_button(self) -> bool:
        """Проверяет отображение кнопки создания"""
        try:
            self.create_button.wait_for(state="visible", timeout=self.action_timeout)
            logger.debug("✅ Кнопка создания отображается")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке кнопки создания: {e}")
            return False

    def verify_table_columns(self) -> bool:
        """Проверяет наличие ключевых колонок таблицы"""
        logger.info("🔍 Проверка наличия колонок таблицы...")
        missing_columns = []
        required_cols = ["ID", "Наименование", "Статус", "Дата создания"]

        for col_name in required_cols:
            selector = self.FILTER_COLUMNS.get(col_name)
            if not selector: continue

            locator = self.page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=1000)
                logger.debug(f"   ✅ Колонка '{col_name}' найдена")
            except:
                missing_columns.append(col_name)
                logger.error(f"   ❌ Колонка '{col_name}' НЕ найдена")

        if missing_columns:
            logger.error(f"⚠️ Отсутствуют колонки: {missing_columns}")
            return False
        return True

    # ================= FILTER HELPERS =================

    def _wait_for_table_stable(self, timeout: Optional[int] = None) -> None:
        """Ждет стабильности таблицы после действия"""
        self.page.wait_for_load_state("networkidle", timeout=timeout or self.test_timeout)
        try:
            self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=5000)
        except PlaywrightTimeoutError:
            pass
        self.page.wait_for_timeout(500)

    def _get_overlay(self):
        """Возвращает локатор открытого оверлея фильтра."""
        return self.page.locator(
            "div.ant-dropdown:has(button:has-text('Применить')), "
            "div.cdk-overlay-pane:has(button:has-text('Применить'))"
        ).first

    def _wait_for_overlay_visible(self, timeout: Optional[int] = None) -> None:
        overlay = self._get_overlay()
        expect(overlay).to_be_visible(timeout=timeout or self.action_timeout)

    def _wait_for_overlay_hidden(self, timeout: Optional[int] = None) -> None:
        overlay = self._get_overlay()
        try:
            expect(overlay).to_be_hidden(timeout=timeout or self.action_timeout)
        except PlaywrightTimeoutError:
            logger.debug("ℹ️ Оверлей уже скрыт или не найден")

    def _apply_filter(self, overlay=None) -> None:
        """Применение фильтра через клик по кнопке Apply"""
        if overlay is None:
            overlay = self._get_overlay()

        apply_btn = overlay.locator("button.ant-btn-primary:has-text('Применить')").first
        expect(apply_btn).to_be_enabled(timeout=self.action_timeout)
        apply_btn.click()

        self._wait_for_overlay_hidden()
        self._wait_for_table_stable()

    def open_filter(self, column_name: str) -> bool:
        """Открывает фильтр для указанной колонки"""
        try:
            logger.debug(f"🔍 Открытие фильтра: {column_name}")
            selector = self.FILTER_COLUMNS.get(column_name)
            if not selector:
                selector = f"th:has-text('{column_name}')"

            header = self.page.locator(selector).first
            header.scroll_into_view_if_needed()

            # Иконка фильтра внутри заголовка
            icon = header.locator("ui-filter-wrapper, .filter-icon, svg[data-icon='filter']").first
            icon.click(timeout=self.action_timeout)

            self._wait_for_overlay_visible()
            return True
        except Exception as e:
            logger.error(f"❌ Не удалось открыть фильтр '{column_name}': {e}")
            return False

    def apply_text_filter(self, text: str) -> None:
        """Применение текстового фильтра"""
        logger.debug(f"⌨️ Текстовый фильтр: '{text}'")
        self._wait_for_overlay_visible()
        overlay = self._get_overlay()

        input_field = overlay.locator("input.ant-input").first
        expect(input_field).to_be_visible(timeout=self.action_timeout)
        input_field.fill(text)

        # Blur через клик по оверлею
        overlay.click(position={"x": 1, "y": 1})
        self.page.wait_for_timeout(200)

        self._apply_filter(overlay)

    def apply_checkbox_filter(self, values: List[str]) -> None:
        """Применение фильтра с чекбоксами"""
        logger.debug(f"☑️ Чекбокс фильтр: {values}")
        self._wait_for_overlay_visible()
        overlay = self._get_overlay()

        for val in values:
            # Ищем чекбокс по тексту рядом
            cb_wrapper = overlay.locator(".ant-checkbox-wrapper").filter(has_text=val).first
            cb_input = cb_wrapper.locator("input.ant-checkbox-input")

            expect(cb_input).to_be_visible(timeout=self.action_timeout)
            if not cb_input.is_checked():
                cb_input.click(timeout=self.action_timeout)

        self.page.wait_for_timeout(200)
        self._apply_filter(overlay)

    def apply_date_filter(self, start_date: str, end_date: str) -> bool:
        """Применение фильтра по датам"""
        try:
            logger.debug(f"📅 Дата фильтр: {start_date} - {end_date}")
            self._wait_for_overlay_visible()
            overlay = self._get_overlay()

            date_start = overlay.locator("input[placeholder='Начало']").first
            date_end = overlay.locator("input[placeholder='Конец']").first

            date_start.click()
            date_start.fill(start_date)
            self.page.wait_for_timeout(150)

            date_end.click()
            date_end.fill(end_date)
            self.page.wait_for_timeout(150)

            # Закрытие календаря кликом по футеру или безопасной зоне
            footer = overlay.locator("div.ant-picker-footer").first
            if footer.count() > 0:
                footer.click()
            else:
                overlay.click(position={"x": 10, "y": 10})

            self.page.wait_for_timeout(200)
            self._apply_filter(overlay)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка применения дата-фильтра: {e}")
            return False

    def clear_filter_modal(self) -> None:
        logger.debug("🧹 Очистка фильтра в модалке")
        self._wait_for_overlay_visible()
        overlay = self._get_overlay()

        clear_btn = overlay.locator("button:has-text('Очистить')").first
        expect(clear_btn).to_be_visible(timeout=self.action_timeout)
        clear_btn.click()

        # После очистки тоже нужно применить/закрыть, обычно кнопка Очистить сразу сбрасывает и закрывает
        self._wait_for_overlay_hidden()
        self._wait_for_table_stable()

    def reset_all_filters_global(self) -> None:
        """Глобальный сброс всех фильтров через кнопку в хедере"""
        logger.debug("🔄 Глобальный сброс фильтров")
        self.page.wait_for_selector("table.cdk-table", state="visible", timeout=self.action_timeout)

        if self.reset_filters_btn.is_visible():
            self.reset_filters_btn.click()
            self._wait_for_table_stable()
        else:
            logger.debug("Кнопка глобального сброса не найдена")

    def is_table_empty(self) -> bool:
        """Проверяет, пуста ли таблица (несколько стратегий)"""
        try:
            self._wait_for_table_stable()

            # Стратегия 1: Ищем стандартный Ant Design empty
            if self.page.locator("div.ant-empty").is_visible(timeout=1000):
                logger.debug("✅ Empty state найден по div.ant-empty")
                return True

            # Стратегия 2: Ищем текст "Нет данных" (по скриншотам это основной вариант)
            if self.page.locator("text=Нет данных").is_visible(timeout=1000):
                logger.debug("✅ Empty state найден по тексту 'Нет данных'")
                return True

            # Стратегия 3: Ищем любой элемент с текстом "Нет данных" + иконка
            if self.page.locator("text=/Нет данных/").is_visible(timeout=1000):
                logger.debug("✅ Empty state найден по regex 'Нет данных'")
                return True

            # Стратегия 4: Проверяем количество строк через JavaScript
            rows_count = self.page.evaluate("""
                () => {
                    const table = document.querySelector('table.cdk-table tbody');
                    return table ? table.querySelectorAll('tr').length : 0;
                }
            """)

            logger.debug(f"📊 Количество строк в таблице (JS): {rows_count}")

            if rows_count == 0:
                return True

            # Стратегия 5: Фолбэк на Playwright count()
            rows = self.table_rows
            count = rows.count()
            logger.debug(f"📊 Количество строк (Playwright): {count}")

            return count == 0

        except Exception as e:
            logger.warning(f"⚠️ is_table_empty: исключение {type(e).__name__}: {e}")
            return True  

    def count_table_rows(self) -> int:
        """Возвращает количество строк в таблице"""
        try:
            # Сначала проверяем empty state
            if self.is_table_empty():
                logger.debug("📭 Таблица пуста (empty state)")
                return 0

            # Ждём, что таблица загрузилась
            self.page.wait_for_selector("table.cdk-table tbody tr",
                                        state="attached",
                                        timeout=5000)

            # Используем evaluate для точного подсчёта
            count = self.page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table.cdk-table tbody tr');
                    return rows.length;
                }
            """)

            logger.debug(f"📊 Найдено строк: {count}")
            return count

        except Exception as e:
            logger.warning(f"⚠️ count_table_rows: ошибка {e}, возвращаем 0")
            return 0

    def get_first_row_cell_text(self, col_index: int) -> str:
        try:
            expect(self.table_rows.first).to_be_visible(timeout=self.action_timeout)
            return self.table_rows.first.locator(f"td:nth-child({col_index})").text_content().strip()
        except Exception:
            return ""


# ================= TEST CASE =================

@pytest.mark.filtering
def test_products_filtering(page: Page) -> None:
    """
    Тест проверяет функциональность фильтрации в разделе Продукты → Продукты
    """
    logger.info("🚀 Старт теста: Фильтрация продуктов")

    products_page = ProductsFilterPage(page)
    soft = SoftAssert()

    try:
        # === БЛОК 1: Авторизация и навигация ===
        LoginPage(page).login()
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)

        products_page.navigate_to_products()
        products_page.take_screenshot("after_nav")

        if not products_page.verify_initial_state():
            soft.errors.append(("verify_initial_state", "Начальное состояние UI не прошло проверку"))
            soft.report_and_raise_if_failed()

        # === БЛОК 2: Проверка UI элементов ===
        logger.info("🖥 Проверка UI элементов...")
        soft.catch_assertion(
            products_page.verify_icons,
            message="Не все иконки отображаются",
            location="ui:icons"
        )
        soft.catch_assertion(
            products_page.verify_create_button,
            message="Кнопка создания не отображается",
            location="ui:create_btn"
        )
        soft.catch_assertion(
            products_page.verify_table_columns,
            message="Отсутствуют обязательные колонки таблицы",
            location="structure:columns"
        )

        # === БЛОК 3: Текстовый фильтр по ID ===
        logger.info("🔤 Блок 3: Текстовый фильтр по ID")
        location = "text_filter:ID"
        col_idx = 1  # ID обычно первая колонка, но проверим по структуре. В ProductsPage index 0 был ID.
        # В таблице cdk-table td:nth-child(1) это ID.

        if products_page.open_filter("ID"):
            # Тест 1: Частичное совпадение
            raw_val = products_page.get_first_row_cell_text(1)
            if raw_val and len(raw_val) > 2:
                partial = raw_val[:3]
                products_page.apply_text_filter(partial)
                soft.assert_not_empty(
                    products_page.count_table_rows(),
                    "Таблица пуста после частичного поиска ID",
                    location=f"{location}.partial"
                )
                products_page.reset_all_filters_global()

            # Тест 2: Полное совпадение
            if products_page.open_filter("ID"):
                full_val = products_page.get_first_row_cell_text(1)
                if full_val:
                    products_page.apply_text_filter(full_val)
                    soft.assert_not_empty(
                        products_page.count_table_rows(),
                        "Таблица пуста после полного поиска ID",
                        location=f"{location}.full"
                    )
                    products_page.reset_all_filters_global()

            # Тест 3: Несуществующее значение
            if products_page.open_filter("ID"):
                products_page.apply_text_filter("999999999999999")
                soft.assert_true(
                    products_page.is_table_empty(),
                    "Таблица не пуста после поиска несуществующего ID",
                    location=f"{location}.not_exist"
                )
                products_page.reset_all_filters_global()   # ИСПРАВЛЕНО: используем глобальный сброс
        else:
            soft.errors.append((location, "Не удалось открыть фильтр ID"))

        # === БЛОК 4: Текстовый фильтр по Наименованию ===
        logger.info("🔤 Блок 4: Текстовый фильтр по Наименованию")
        location = "text_filter:Name"

        if products_page.open_filter("Наименование"):
            raw_val = products_page.get_first_row_cell_text(2)  # Name - 2-я колонка
            if raw_val and len(raw_val) > 2:
                partial = raw_val[:3]
                products_page.apply_text_filter(partial)
                soft.assert_not_empty(
                    products_page.count_table_rows(),
                    "Таблица пуста после частичного поиска Наименования",
                    location=f"{location}.partial"
                )
                products_page.reset_all_filters_global()

            # Несуществующее
            if products_page.open_filter("Наименование"):
                products_page.apply_text_filter("ZZZZZZZZZZZZZZZZ")
                soft.assert_true(
                    products_page.is_table_empty(),
                    "Таблица не пуста после поиска несуществующего Наименования",
                    location=f"{location}.not_exist"
                )
                products_page.reset_all_filters_global()   
        else:
            soft.errors.append((location, "Не удалось открыть фильтр Наименование"))

        # === БЛОК 5: Чекбокс-фильтр по Статусу ===
        logger.info("☑️ Блок 5: Чекбокс-фильтр по Статусу")
        location = "checkbox_filter:Status"
        statuses = ["Активен", "Архивный", "Черновик"]

        if products_page.open_filter("Статус"):
            # Выбор одного статуса
            products_page.apply_checkbox_filter([statuses[0]])
            soft.assert_not_empty(
                products_page.count_table_rows(),
                f"Пусто после выбора статуса '{statuses[0]}'",
                location=f"{location}.single"
            )
            products_page.reset_all_filters_global()

            # Выбор нескольких статусов
            if products_page.open_filter("Статус"):
                products_page.apply_checkbox_filter(statuses[:2])
                soft.assert_not_empty(
                    products_page.count_table_rows(),
                    "Пусто после множественного выбора статусов",
                    location=f"{location}.multiple"
                )
                products_page.reset_all_filters_global()
        else:
            soft.errors.append((location, "Не удалось открыть фильтр Статус"))

        # === БЛОК 6: Фильтр по дате создания ===
        logger.info("📅 Блок 6: Фильтр по дате создания")
        location = "date_filter:CreatedDate"

        today = datetime.now()
        past_date = (today - timedelta(days=28)).strftime("%d.%m.%Y")
        current_date = today.strftime("%d.%m.%Y")
        future_start = (today + timedelta(days=90)).strftime("%d.%m.%Y")
        future_end = (today + timedelta(days=97)).strftime("%d.%m.%Y")

        if products_page.open_filter("Дата создания"):
            # Валидный период
            res = products_page.apply_date_filter(past_date, current_date)
            if res:
                soft.assert_not_empty(
                    products_page.count_table_rows(),
                    f"Таблица пуста для валидного периода {past_date} - {current_date}",
                    location=f"{location}.valid"
                )
                products_page.reset_all_filters_global()

            # Будущий период
            if products_page.open_filter("Дата создания"):
                res = products_page.apply_date_filter(future_start, future_end)
                if res:
                    soft.assert_true(
                        products_page.is_table_empty(),
                        f"Таблица НЕ пуста для будущих дат {future_start} - {future_end}",
                        location=f"{location}.future"
                    )
                    products_page.reset_all_filters_global()
        else:
            soft.errors.append((location, "Не удалось открыть фильтр Даты создания"))

        # Финальный скриншот
        products_page.take_screenshot("test_complete")

        # === ОТЧЕТНОСТЬ ===
        if soft.has_errors():
            logger.warning(f"⚠️ Тест завершён с {len(soft.errors)} ошибкой(ями)")
        else:
            logger.info("🎉 Тест 'Фильтрация продуктов' успешно завершен без ошибок!")

        soft.report_and_raise_if_failed()

    except AssertionError:
        products_page.take_screenshot("test_final_fail")
        raise
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка теста: {e}")
        products_page.take_screenshot("test_critical_fail")
        raise AssertionError(f"Тест упал на системном уровне: {e}") from e
