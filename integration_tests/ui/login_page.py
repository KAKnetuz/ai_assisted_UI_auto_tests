import os
import re
import uuid
import logging
from datetime import datetime
from playwright.sync_api import Page, expect, Locator, TimeoutError as PlaywrightTimeoutError
from integration_tests.ui.config import Config

logger = logging.getLogger(__name__)

class LoginPage:
    def __init__(self, page: Page):
        self.page = page

    def login(self, username: str = None, password: str = None) -> None:
        username = username or Config.TEST_USERNAME
        password = password or Config.TEST_PASSWORD
        logger.info(f"🔐 Начало авторизации: {username}")
        auth_url = self._build_auth_url()
        logger.debug(f"🌐 Переход: {auth_url}")
        self.page.goto(auth_url, wait_until=Config.WAIT_UNTIL, timeout=Config.AUTH_TIMEOUT)
        self._wait_for_keycloak_form()
        logger.debug("👤 Поиск поля логина...")
        username_field = self._find_username_field()
        expect(username_field).to_be_visible(timeout=Config.AUTH_TIMEOUT)
        username_field.fill(username)
        self._blur_fields()
        password_field = self._find_password_field()
        if password_field and password_field.is_visible(timeout=2000):
            logger.debug("🔑 Обнаружена одноэтапная форма")
            password_field.fill(password)
            self._blur_fields()
            self._click_submit_button()
        else:
            logger.debug("🔘 Клик по кнопке 'Вход' (этап 1)...")
            self._click_submit_button()
            logger.debug("🔑 Ожидание поля пароля...")
            password_field = self._find_password_field()
            if password_field:
                expect(password_field).to_be_visible(timeout=Config.AUTH_TIMEOUT)
                password_field.fill(password)
                self._blur_fields()
                logger.debug("🔘 Клик по кнопке 'Вход' (этап 2)...")
                self._click_submit_button()
                logger.debug("✅ Пароль введён, форма отправлена")
            else:
                self._take_debug_screenshot("password_field_not_found")
                raise RuntimeError("Поле пароля не найдено после первого этапа")
        logger.debug("🔄 Ожидание редиректа...")
        try:
            self.page.wait_for_url(
                lambda url: (
                    Config.BASE_URL in url
                    and "/auth" not in url
                    and "/realms" not in url
                ),
                timeout=Config.AUTH_TIMEOUT
            )
        except PlaywrightTimeoutError:
            self._take_debug_screenshot("redirect_timeout")
            raise
        logger.debug("🏗 Проверка загрузки приложения...")
        self._wait_for_app_loaded()
        logger.info("✅ Авторизация успешно завершена")

    def is_on_login_page(self) -> bool:
        try:
            return self._find_username_field().is_visible(timeout=2000)
        except (PlaywrightTimeoutError, Exception):
            return False

    def _wait_for_keycloak_form(self) -> None:
        logger.debug("⏳ Ожидание загрузки формы Keycloak...")
        form_selectors = [
            "#kc-form-login",
            "form[action*='login']",
            ".login-pf-page",
            "[id*='keycloak']",
            "div[class*='login']",
        ]
        for selector in form_selectors:
            try:
                self.page.wait_for_selector(
                    selector, state="visible", timeout=5000
                )
                logger.debug(f"✅ Форма Keycloak найдена: {selector}")
                return
            except PlaywrightTimeoutError:
                continue
        logger.warning("⚠️ Стандартная форма Keycloak не найдена, продолжаем")
        self._take_debug_screenshot("keycloak_form_not_found")

    def _find_username_field(self) -> Locator:
        candidates = [
            ("get_by_role", 'textbox', "Имя пользователя или E-mail"),
            ("get_by_role", 'textbox', "Username"),
            ("get_by_role", 'textbox', "Логин"),
            ("css", 'input[name="username"]'),
            ("css", 'input[name="email"]'),
            ("css", 'input[type="email"]'),
            ("css", '#username'),
            ("css", '#email'),
            ("css", 'input[placeholder*="E-mail"]'),
            ("css", 'input[placeholder*="email" i]'),
            ("css", 'input[placeholder*="логин" i]'),
        ]
        for candidate in candidates:
            locator = self._resolve_locator(candidate)
            if locator and self._is_visible_safe(locator, timeout=1000):
                logger.debug(f"   ✅ Поле логина найдено: {candidate}")
                return locator
        logger.error("❌ Поле логина не найдено ни одним из селекторов")
        self._take_debug_screenshot("username_field_not_found")
        return self._resolve_locator(candidates[0])

    def _find_password_field(self) -> Locator | None:
        candidates = [
            ("get_by_role", 'textbox', "Пароль"),
            ("css", 'input[name="password"]'),
            ("css", 'input[type="password"]'),
            ("css", '#password'),
        ]
        for candidate in candidates:
            locator = self._resolve_locator(candidate)
            if locator and self._is_visible_safe(locator, timeout=1000):
                logger.debug(f"   ✅ Поле пароля найдено: {candidate}")
                return locator
        return None

    def _click_submit_button(self) -> None:
        candidates = [
            ("get_by_role", 'button', "Вход"),
            ("get_by_role", 'button', "Войти"),
            ("get_by_role", 'button', "Log in"),
            ("get_by_role", 'button', "Next"),
            ("css", 'input[type="submit"]'),
            ("css", 'button[type="submit"]'),
            ("css", '#kc-login'),
            ("css", 'button.btn-primary'),
        ]
        for candidate in candidates:
            locator = self._resolve_locator(candidate)
            if locator and self._is_visible_safe(locator, timeout=1000):
                try:
                    if locator.is_enabled(timeout=1000):
                        logger.debug(f"   ✅ Кнопка найдена: {candidate}")
                        locator.click(timeout=Config.ACTION_TIMEOUT)
                        return
                except (PlaywrightTimeoutError, Exception):
                    continue
        self._take_debug_screenshot("submit_button_not_found")
        raise RuntimeError("Кнопка отправки формы не найдена")

    def _resolve_locator(self, candidate: tuple) -> Locator | None:
        try:
            if candidate[0] == "get_by_role":
                return self.page.get_by_role(candidate[1], name=candidate[2]).first
            elif candidate[0] == "css":
                return self.page.locator(candidate[1]).first
        except Exception:
            return None
        return None

    def _is_visible_safe(self, locator: Locator, timeout: int = 1000) -> bool:
        try:
            return locator.is_visible(timeout=timeout)
        except (PlaywrightTimeoutError, Exception):
            return False

    def _blur_fields(self) -> None:
        try:
            self.page.locator("body").click(position={"x": 1, "y": 1})
        except Exception:
            pass

    def _wait_for_app_loaded(self) -> None:
        app_selectors = [
            "app-root",
            "[data-test-id='app-root']",
            "[id='root']"
        ]
        for selector in app_selectors:
            try:
                self.page.wait_for_selector(
                    selector, state="visible",
                    timeout=Config.WAIT_FOR_SELECTOR_TIMEOUT
                )
                logger.debug(f"✅ Приложение найдено: {selector}")
                return
            except PlaywrightTimeoutError:
                continue
        logger.warning("⚠️ Элемент приложения не найден, ждём networkidle")
        try:
            self.page.wait_for_load_state("networkidle", timeout=Config.NETWORK_IDLE_TIMEOUT)
        except PlaywrightTimeoutError:
            pass

    def _take_debug_screenshot(self, name: str) -> None:
        try:
            os.makedirs("results", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"results/debug_{name}_{timestamp}.png"
            self.page.screenshot(path=path, full_page=True)
            logger.info(f"📸 Отладочный скриншот: {path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сделать скриншот: {e}")

    def _build_auth_url(self) -> str:
        redirect_uri = f"{Config.BASE_URL}/profile/settings"
        state = str(uuid.uuid4())
        nonce = str(uuid.uuid4())
        params = (
            f"?client_id=app"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&response_mode=fragment"
            f"&response_type=code"
            f"&scope=openid"
            f"&nonce={nonce}"
            f"&code_challenge=<pkce-challenge>"
            f"&code_challenge_method=S256"
        )
        return f"{Config.AUTH_URL}{params}"
