"""Настройка логирования и маскирование чувствительных данных."""

import logging
import re

_SENSITIVE_RE = re.compile(
    r"(?i)(password|passwd|token|secret|authorization|code_verifier)([\"']?\s*[:=]\s*[\"']?)([^\s\"'&,}]+)"
)
_BEARER_RE = re.compile(r"(?i)(bearer\s+)[\w.\-~+/]+=*")


def mask_sensitive(text: str) -> str:
    """Скрывает значения паролей, токенов и заголовков авторизации в строке."""
    text = _BEARER_RE.sub(r"\1***", text)
    return _SENSITIVE_RE.sub(r"\1\2***", text)


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_sensitive(record.getMessage())
        record.args = None
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, MaskingFilter) for f in logger.filters):
        logger.addFilter(MaskingFilter())
    return logger
