"""Мягкие проверки: собирают все ошибки и падают один раз с полным отчётом."""

import logging

logger = logging.getLogger(__name__)


class SoftAssert:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []

    def check(self, condition: bool, message: str, location: str = "") -> bool:
        if not condition:
            self.errors.append((location, message))
            logger.error(f"[{location}] {message}")
        return condition

    def assert_all(self) -> None:
        if self.errors:
            report = "\n".join(f"  [{loc}] {msg}" for loc, msg in self.errors)
            raise AssertionError(f"Найдено ошибок: {len(self.errors)}\n{report}")
