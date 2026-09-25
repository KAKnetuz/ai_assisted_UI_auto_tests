"""
Конфигурация UI-тестов.
Загружает настройки из переменных окружения / .env файла через pydantic-settings.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_INTEGRATION_TESTS_DIR: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_INTEGRATION_TESTS_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    BASE_URL: str = "https://app.example.com"
    TEST_USERNAME: str = "demo_user"
    TEST_PASSWORD: str = ""

    # Таймауты, мс
    ACTION_TIMEOUT: int = 10_000
    EXPECT_TIMEOUT: int = 15_000
    NAVIGATION_TIMEOUT: int = 45_000
    AUTH_TIMEOUT: int = 45_000

    # Браузерный контекст
    VIEWPORT_WIDTH: int = 1600
    VIEWPORT_HEIGHT: int = 1200
    LOCALE: str = "ru-RU"
    TIMEZONE: str = "Europe/Moscow"
    IGNORE_HTTPS_ERRORS: bool = False

    @property
    def context_args(self) -> dict:
        """Аргументы для browser.new_context()."""
        return {
            "base_url": self.BASE_URL,
            "viewport": {"width": self.VIEWPORT_WIDTH, "height": self.VIEWPORT_HEIGHT},
            "locale": self.LOCALE,
            "timezone_id": self.TIMEZONE,
            "ignore_https_errors": self.IGNORE_HTTPS_ERRORS,
        }


settings = Settings()
