"""
Авторизация через SSO (Keycloak).

Приложение само перенаправляет на страницу входа и само строит OAuth-параметры
(state, nonce, PKCE), поэтому тест открывает только BASE_URL.
"""

from playwright.sync_api import expect

from integration_tests.config.constants import APP_ROOT
from integration_tests.pages.base_page import BasePage
from integration_tests.utils.logger import get_logger

logger = get_logger(__name__)

USERNAME_INPUT = "#username, input[name='username'], input[type='email']"
PASSWORD_INPUT = "#password, input[name='password'], input[type='password']"
SUBMIT_BUTTON = "#kc-login, button[type='submit'], input[type='submit']"


class LoginPage(BasePage):
    @property
    def app_root(self):
        return self.page.locator(APP_ROOT).first

    @property
    def username(self):
        return self.page.locator(USERNAME_INPUT).first

    @property
    def password(self):
        return self.page.locator(PASSWORD_INPUT).first

    @property
    def submit(self):
        return self.page.locator(SUBMIT_BUTTON).first

    def open_app(self) -> None:
        """Открывает приложение и логинится, только если SSO-сессии ещё нет."""
        timeout = self.settings.AUTH_TIMEOUT
        self.page.goto(self.settings.BASE_URL, timeout=timeout)
        # Ждём либо приложение (SSO-сессия уже есть), либо форму входа; скрытые элементы не учитываются
        app_or_login = self.page.locator(f"{APP_ROOT}, {USERNAME_INPUT}").filter(visible=True).first
        expect(app_or_login).to_be_visible(timeout=timeout)
        if self.username.is_visible():
            self.login()

    def login(self, username: str | None = None, password: str | None = None) -> None:
        username = username or self.settings.TEST_USERNAME
        password = password or self.settings.TEST_PASSWORD
        timeout = self.settings.AUTH_TIMEOUT
        logger.info(f"Авторизация пользователя {username}")

        expect(self.username).to_be_visible(timeout=timeout)
        self.username.fill(username)

        # Двухшаговая форма: поле пароля появляется после отправки логина
        if not self.password.is_visible():
            self.submit.click()
            expect(self.password).to_be_visible(timeout=timeout)
        self.password.fill(password)
        self.submit.click()

        self.page.wait_for_url(
            lambda url: url.startswith(self.settings.BASE_URL) and "/realms/" not in url,
            timeout=timeout,
        )
        expect(self.app_root).to_be_visible(timeout=timeout)
        logger.info("Авторизация завершена")
