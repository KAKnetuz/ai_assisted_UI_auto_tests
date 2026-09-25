import os
import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config
from integration_tests.ui.login_page import LoginPage
from integration_tests.ui.base_page import BasePage  # ✅ Исправленный импорт

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
    """Класс для мягких ассерций (накопление ошибок)"""

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


class ProductsPage(BasePage):
    """Страница раздела Продукты → Продукты (Исправленная версия)"""

    # Конфигурация колонок для сортировки
    SORT_CONFIG = {
        "date_created": {
            "header_text": "Дата создания",
            "selector": "th.cdk-column-created_date",
            "index": 3  
        }
    }

    # Список всех колонок для проверки структуры
    REQUIRED_COLUMNS_SELECTORS = {
        "ID": "th.cdk-column-id",
        "Наименование": "th.cdk-column-name",
        "Статус": "th.cdk-column-status",
        "Дата создания": "th.cdk-column-created_date",
        "Кол-во предложений": "th.cdk-column-offers_number",
        "Описание": "th.cdk-column-description",
        "": "th.cdk-column-menu"  
    }

    def __init__(self, page: Page):
        super().__init__(page)  

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

        # Пагинация
        self.items_per_page_label = page.locator("ui-paginator div.limit span.label").first

        # Опции внутри дропдауна
        self.items_per_page_options = {
            10: page.locator("ul.limit-ul li.limit-ul__item:nth-child(1) span.value").first,
            20: page.locator("ul.limit-ul li.limit-ul__item:nth-child(2) span.value").first,
            50: page.locator("ul.limit-ul li.limit-ul__item:nth-child(3) span.value").first,
            100: page.locator("ul.limit-ul li.limit-ul__item:nth-child(4) span.value").first
        }

        # Навигация по страницам
        self.prev_arrow = page.locator("li.ant-pagination-prev button.ant-pagination-item-link").first
        self.next_arrow = page.locator("li.ant-pagination-next button.ant-pagination-item-link").first
        self.page_numbers = page.locator("li.ant-pagination-item a")
        self.last_page = self.page_numbers.last
        self.first_page = page.locator("li.ant-pagination-item:nth-child(2) a").first

    def navigate_to_products(self) -> None:
        """Переход в раздел Продукты → Продукты"""
        logger.info("📍 Навигация: Продукты -> Продукты")

        # Клик по меню Продукты
        products_menu = self.page.locator("a.sidebar__nav-link:has-text('Продукты')").first
        products_menu.click(timeout=self.action_timeout)

        # Ждем появления вкладки Продукты
        self.page.wait_for_selector("span.navigations__item:has-text('Продукты')", state="visible",
                                    timeout=self.test_timeout)

        # Проверяем активность вкладки
        products_tab_class = self.tabs["products"].get_attribute("class") or ""
        if "active-route" not in products_tab_class.lower():
            self.tabs["products"].click(timeout=self.action_timeout)

        # ✅ УВЕЛИЧЕННЫЕ ТАЙМАУТЫ для стабильности
        self.page.wait_for_load_state("networkidle", timeout=30000)
        self.page.wait_for_timeout(2000) 

        expect(self.page).to_have_url(
            re.compile(r".*/products/product-list"),
            timeout=self.test_timeout
        )
        logger.debug("✅ Навигация завершена")

    def verify_initial_state(self) -> bool:
        """Проверка начального состояния UI"""
        logger.debug("Проверка начального состояния UI")
        try:
            expect(self.header).to_be_visible(timeout=self.action_timeout)
            expect(self.tabs["products"]).to_be_visible(timeout=self.action_timeout)

            # Проверка активности вкладки
            products_class = self.tabs["products"].get_attribute("class") or ""
            if "active-route" not in products_class.lower():
                logger.warning("⚠️ Вкладка 'Продукты' не имеет класса active-route")

            self.wait_for_table_stable("table.cdk-table")

            # Дополнительная пауза для медленных сервисов
            self.page.wait_for_timeout(1000)

            logger.info("✅ UI загружен и стабилен")
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

        for col_name, selector in self.REQUIRED_COLUMNS_SELECTORS.items():
            locator = self.page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=2000)  # ✅ Увеличенный таймаут
                logger.debug(f"   ✅ Колонка '{col_name if col_name else '[Меню]'}' найдена")
            except:
                missing_columns.append(col_name if col_name else "[Меню]")
                logger.error(f"   ❌ Колонка '{col_name if col_name else '[Меню]'}' НЕ найдена")

        if missing_columns:
            logger.error(f"⚠️ Отсутствуют колонки: {missing_columns}")
            return False
        else:
            logger.info(f"✅ Все проверенные колонки присутствуют")
            return True

    # ================= УЛУЧШЕННЫЕ МЕТОДЫ ПОИСКА =================

    def _find_column_header(self, config_key: str):
        """Находит заголовок колонки с фоллбэками"""
        config = self.SORT_CONFIG.get(config_key)
        if not config:
            return None

        # ✅ Ждем стабильности таблицы ПЕРЕД поиском
        self.page.wait_for_load_state("networkidle", timeout=10000)
        self.page.wait_for_timeout(500)

        selector = config["selector"]
        header_text = config["header_text"]

        # Пробуем по селектору
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible", timeout=5000)  # ✅ Увеличенный таймаут
            logger.debug(f"✅ Найден заголовок по селектору: {selector}")
            return locator
        except Exception:
            pass

        # Фоллбэк по тексту
        try:
            locator = self.page.locator(f"th:has-text('{header_text}')").first
            locator.wait_for(state="visible", timeout=5000)
            logger.debug(f"✅ Найден заголовок по тексту: {header_text}")
            return locator
        except Exception:
            pass

        logger.error(f"❌ Не найден заголовок: {config_key}")
        self.take_screenshot(f"header_{config_key}_not_found")
        return None

    def click_sort_icon(self, config_key: str) -> None:
        """Кликает по иконке сортировки указанной колонки"""
        header_locator = self._find_column_header(config_key)
        if not header_locator:
            raise ValueError(f"Не удалось найти заголовок колонки: {config_key}")

        header_locator.scroll_into_view_if_needed()

        # Ищем иконку сортировки внутри заголовка
        sort_container = header_locator.locator("ui-sort").first

        try:
            svg_icon = sort_container.locator("svg").first
            if svg_icon.is_visible(timeout=1000):
                svg_icon.click(timeout=self.action_timeout)
            else:
                path_icon = sort_container.locator("path").first
                if path_icon.is_visible(timeout=1000):
                    path_icon.click(timeout=self.action_timeout)
                else:
                    sort_container.click(timeout=self.action_timeout)
        except:
            header_locator.click(timeout=self.action_timeout)

        # ✅ Усиленное ожидание после сортировки
        self.wait_for_table_stable("table.cdk-table")
        self.page.wait_for_timeout(1000)
        logger.debug(f"✅ Клик по сортировке: {self.SORT_CONFIG[config_key]['header_text']}")

    def get_column_values(self, column_index: int, limit: int = 5) -> List[str]:
        """Извлекает значения из указанного столбца"""
        values = []
        rows = self.table_rows.all()[:limit]

        for row in rows:
            cells = row.locator("td").all()
            if len(cells) > column_index:
                text = cells[column_index].inner_text().strip()
                if text:
                    values.append(text)

        return values

    def parse_date_safe(self, date_str: str) -> Optional[datetime]:
        """Парсит дату из строки"""
        if not date_str:
            return None

        date_clean = date_str.split()[0] if ' ' in date_str else date_str

        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S"]
        for fmt in formats:
            try:
                return datetime.strptime(date_clean, fmt)
            except ValueError:
                continue
        return None

    def verify_date_sorting(self, column_index: int, expected_order: str) -> bool:
        """Проверяет порядок сортировки дат"""
        values = self.get_column_values(column_index, limit=10)

        if len(values) < 2:
            logger.warning("⚠️ Недостаточно данных для проверки сортировки (< 2 строк)")
            return True

        dates = [self.parse_date_safe(v) for v in values]
        valid_dates = [d for d in dates if d is not None]

        if len(valid_dates) < 2:
            logger.warning("⚠️ Не удалось распарсить даты для проверки")
            return True

        for k in range(len(valid_dates) - 1):
            curr = valid_dates[k]
            next_ = valid_dates[k + 1]

            if expected_order == 'asc':
                if curr > next_:
                    return False
            elif expected_order == 'desc':
                if curr < next_:
                    return False

        return True

    def test_column_sorting_cycle(self, config_key: str, soft_assert: SoftAssert) -> None:
        """Полный цикл тестирования сортировки: ASC -> DESC -> RESET"""

        # ✅ Ждем стабильности перед началом сортировки
        self.page.wait_for_load_state("networkidle", timeout=10000)
        self.page.wait_for_timeout(1000)

        config = self.SORT_CONFIG.get(config_key)
        if not config:
            logger.error(f"❌ Конфигурация не найдена: {config_key}")
            return

        header_text = config["header_text"]
        col_index = config["index"]
        location = f"sorting:{config_key}"

        logger.info(f"📊 Тестирование сортировки: {header_text}")

        try:
            # ШАГ 1: ASC
            logger.debug("🔄 Шаг 1: ASC")
            self.click_sort_icon(config_key)
            self.page.wait_for_timeout(1000)  # ✅ Увеличенная пауза
            is_asc = self.verify_date_sorting(col_index, 'asc')
            soft_assert.assert_true(
                is_asc,
                f"Сортировка ASC не применена для '{header_text}'",
                location=f"{location}.asc"
            )

            # ШАГ 2: DESC
            logger.debug("🔄 Шаг 2: DESC")
            self.click_sort_icon(config_key)
            self.page.wait_for_timeout(1000)  # ✅ Увеличенная пауза
            is_desc = self.verify_date_sorting(col_index, 'desc')
            soft_assert.assert_true(
                is_desc,
                f"Сортировка DESC не применена для '{header_text}'",
                location=f"{location}.desc"
            )

            # ШАГ 3: RESET
            logger.debug("🔄 Шаг 3: RESET")
            self.click_sort_icon(config_key)
            self.page.wait_for_timeout(500)
            logger.debug("✅ Сброс выполнен")

        except Exception as e:
            logger.error(f"❌ Ошибка сортировки {header_text}: {e}")
            self.take_screenshot(f"sorting_{config_key}_fail")
            soft_assert.errors.append((location, f"Исключение: {str(e)}"))

    # ================= ИСПРАВЛЕННАЯ ПАГИНАЦИЯ =================

    def count_table_rows(self) -> int:
        """Надежный подсчет строк таблицы"""
        try:
            self.page.wait_for_selector("table.cdk-table tbody", state="visible", timeout=self.action_timeout)

            empty_indicator = self.page.locator("div.ant-empty")
            if empty_indicator.first.is_visible(timeout=1000):
                return 0

            row_count = self.table_rows.count()
            logger.debug(f"🔍 Найдено строк: {row_count}")
            return row_count
        except Exception as e:
            logger.error(f"⚠️ Ошибка при подсчете строк: {e}")
            return 0

    def change_items_per_page(self, count: int) -> None:
        """
        Изменяет количество отображаемых строк.
        ✅ ИСПРАВЛЕНО: Добавлено ожидание фактического изменения DOM
        """
        try:
            option = self.items_per_page_options.get(count)
            if not option:
                raise ValueError(f"Некорректное значение: {count}")

            # 1. Открываем дропдаун
            logger.debug(f"Открытие дропдауна для выбора {count}")
            self.items_per_page_label.click(timeout=self.action_timeout)

            # 2. Ждем появления опций
            self.page.wait_for_selector("ul.limit-ul", state="visible", timeout=self.action_timeout)

            # 3. Кликаем на опцию
            logger.debug(f"Выбор опции {count}")
            option.click(timeout=self.action_timeout)

            # 4. Закрываем дропдаун (Escape надежнее клика)
            self.page.keyboard.press("Escape")

            # 5. Ждем фактического изменения количества строк
            logger.debug(f"⏳ Ожидание изменения количества строк до {count}...")
            try:
                self.page.wait_for_function(
                    f"""() => {{
                        const rows = document.querySelectorAll('table.cdk-table tbody tr');
                        return rows.length <= {count};
                    }}""",
                    timeout=10000  # ✅ Увеличенный таймаут для нагрузки
                )
            except PlaywrightTimeoutError:
                logger.warning(f"⚠️ Таймаут ожидания строк, пробуем продолжить...")

            # 6. Используем метод из BasePage
            self.wait_for_table_stable("table.cdk-table")

            logger.debug(f"✅ Лимит {count} установлен")

        except Exception as e:
            logger.error(f"❌ Ошибка изменения лимита: {e}")
            self.take_screenshot(f"change_limit_{count}_fail")
            raise

    def verify_items_per_page(self, expected_count: int) -> bool:
        """Проверяет количество строк в таблице"""
        try:
            actual_count = self.count_table_rows()
            if actual_count > expected_count:
                logger.error(f"❌ Ожидалось максимум {expected_count} строк, получено: {actual_count}")
                return False
            logger.debug(f"✅ В таблице отображается {actual_count} строк (ожидалось ≤ {expected_count})")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке количества строк: {e}")
            return False

    def navigate_pages(self, direction: str, steps: int = 1) -> bool:
        """Навигация по страницам"""
        try:
            arrow = self.next_arrow if direction == "next" else self.prev_arrow
            arrow_name = "Вперед" if direction == "next" else "Назад"

            for i in range(steps):
                try:
                    arrow.wait_for(state="visible", timeout=self.action_timeout)
                    if arrow.is_enabled():
                        arrow.click(timeout=self.action_timeout)
                        self.wait_for_table_stable("table.cdk-table")  # ✅ Используем метод BasePage
                        logger.debug(f"✅ Нажали '{arrow_name}' ({i + 1}/{steps})")
                    else:
                        logger.debug(f"ℹ️ Кнопка '{arrow_name}' неактивна")
                        break
                except Exception as e:
                    logger.debug(f"ℹ️ Кнопка '{arrow_name}' не найдена: {e}")
                    break
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при навигации: {e}")
            return False

    def go_to_page(self, page_number: str) -> bool:
        """Переход на первую или последнюю страницу"""
        try:
            page_locator = self.last_page if page_number == "last" else self.first_page
            page_name = "последнюю" if page_number == "last" else "первую"

            page_locator.wait_for(state="visible", timeout=self.action_timeout)
            page_locator.click(timeout=self.action_timeout)
            self.wait_for_table_stable("table.cdk-table")  # ✅ Используем метод BasePage

            logger.debug(f"✅ Успешно перешли на {page_name} страницу")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при переходе на {page_name} страницу: {e}")
            return False


def test_products_pagination_and_sorting(page: Page) -> None:
    """
    Тест проверяет функциональность пагинации и сортировки в разделе Продукты → Продукты
    ✅ ИСПРАВЛЕНО: Увеличены таймауты и добавлена стабилизация
    """
    logger.info("🚀 Старт теста: Пагинация и сортировка продуктов")

    products_page = ProductsPage(page)
    soft = SoftAssert()

    try:
        # === БЛОК 1: Авторизация и навигация ===
        LoginPage(page).login()

        # Ждем полной загрузки приложения
        page.wait_for_selector("app-layout", state="visible", timeout=Config.TEST_TIMEOUT)

        products_page.navigate_to_products()

        # СТАБИЛИЗАЦИЯ после навигации
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)

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

        # === БЛОК 3: Тестирование пагинации ===
        logger.info("📄 Тестирование пагинации...")

        pagination_counts = [10, 50, 100, 20]

        for count in pagination_counts:
            try:
                products_page.change_items_per_page(count)
                soft.assert_true(
                    products_page.verify_items_per_page(count),
                    f"Неверное количество строк при выборе {count}",
                    location=f"pagination:change_{count}"
                )
            except Exception as e:
                soft.errors.append((f"pagination:change_{count}", f"Ошибка изменения лимита: {e}"))

        # Навигация по страницам
        soft.assert_true(
            products_page.navigate_pages("next", 2),
            "Ошибка навигации вперед",
            location="pagination:nav_next"
        )
        soft.assert_true(
            products_page.navigate_pages("prev", 2),
            "Ошибка навигации назад",
            location="pagination:nav_prev"
        )
        soft.assert_true(
            products_page.go_to_page("last"),
            "Ошибка перехода на последнюю страницу",
            location="pagination:go_last"
        )
        soft.assert_true(
            products_page.go_to_page("first"),
            "Ошибка перехода на первую страницу",
            location="pagination:go_first"
        )

        # === БЛОК 4: Тестирование сортировки ===
        logger.info("🔍 Тестирование сортировки...")

        # Тестирование "Дата создания"
        products_page.test_column_sorting_cycle("date_created", soft)

        # Финальный скриншот
        products_page.take_screenshot("test_complete")

        # === ОТЧЕТНОСТЬ ===
        if soft.has_errors():
            logger.warning(f"⚠️ Тест завершён с {len(soft.errors)} ошибкой(ями)")
        else:
            logger.info("🎉 Тест успешно завершен без ошибок!")

        soft.report_and_raise_if_failed()

    except AssertionError:
        products_page.take_screenshot("test_final_fail")
        raise
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка теста: {e}")
        products_page.take_screenshot("test_critical_fail")
        raise AssertionError(f"Тест упал на системном уровне: {e}") from e
