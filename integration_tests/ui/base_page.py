import os
import logging
from datetime import datetime
from typing import Optional
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config

logger = logging.getLogger(__name__)


class BasePage:
    """
    Базовый класс для всех Page Objects.
    Содержит общие методы: скриншоты, ожидания, проверки UI.
    """

    def __init__(self, page: Page):
        self.page = page
        self.action_timeout = Config.ACTION_TIMEOUT
        self.test_timeout = Config.TEST_TIMEOUT
        self.results_dir = "results"
        os.makedirs(self.results_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ==================== ОЖИДАНИЯ ====================
    def wait_for_table_stable(self, table_selector: str = "table") -> None:
        """Ожидает стабилизации таблицы (нет спиннера, сеть idle)"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=self.test_timeout)
        except PlaywrightTimeoutError:
            pass
        try:
            self.page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        try:
            expect(self.page.locator(table_selector).first).to_be_visible(timeout=self.test_timeout)
        except Exception:
            pass

    def wait_for_element(self, selector: str, state: str = "visible") -> None:
        """Универсальное ожидание элемента"""
        self.page.wait_for_selector(selector, state=state, timeout=self.action_timeout)

    # ==================== СКРИНШОТЫ ====================
    def take_screenshot(self, name: str, full_page: bool = False) -> str:
        """Делает скриншот и возвращает путь"""
        path = os.path.join(self.results_dir, f"{name}_{self.timestamp}.png")
        try:
            self.page.screenshot(path=path, full_page=full_page)
            logger.debug(f"📸 {path}")
        except Exception as e:
            logger.warning(f"⚠️ Скриншот не сделан: {e}")
        return path

    # ==================== ПРОВЕРКИ UI ====================
    def verify_element_visible(self, locator, name: str = "") -> bool:
        """Проверяет видимость одного элемента"""
        try:
            expect(locator).to_be_visible(timeout=self.action_timeout)
            return True
        except (AssertionError, PlaywrightTimeoutError):
            logger.warning(f"⚠️ Элемент '{name}' не виден")
            return False

    def verify_multiple_elements(self, elements: dict, group_name: str = "") -> bool:
        """
        Проверяет видимость группы элементов (вкладок, иконок и т.д.)
        elements: dict вида {"name": locator}
        """
        missing = []
        for name, locator in elements.items():
            if not self.verify_element_visible(locator, f"{group_name}:{name}"):
                missing.append(name)
        if missing:
            logger.warning(f"⚠️ {group_name}: отсутствуют {missing}")
            return False
        logger.info(f"✅ Все {group_name} ({len(elements)}) отображаются")
        return True

    def verify_table_columns(self, expected_columns: list[str]) -> bool:
        """Проверяет наличие всех ожидаемых колонок в таблице"""
        import re
        missing = []
        for col_name in expected_columns:
            col_clean = col_name.strip()
            if not col_clean:
                continue
            try:
                header = self.page.get_by_role(
                    "columnheader", name=re.compile(re.escape(col_clean))
                )
                if header.count() == 0:
                    missing.append(col_clean)
            except Exception:
                missing.append(col_clean)

        if missing:
            logger.error(f"⚠️ Отсутствуют колонки: {missing}")
            return False
        logger.info(f"✅ Все {len(expected_columns)} колонок на месте")
        return True

    # ==================== НАВИГАЦИЯ ====================
    def click_if_not_active(self, locator, active_class: str = "active") -> None:
        """Кликает по элементу, если он не активен"""
        current_class = locator.get_attribute("class") or ""
        if active_class not in current_class.lower():
            locator.click(timeout=self.action_timeout)