# 🤖 AI-Assisted UI Auto Tests

[![CI](https://github.com/KAKnetuz/ai_assisted_UI_auto_tests/actions/workflows/ci.yml/badge.svg)](https://github.com/KAKnetuz/ai_assisted_UI_auto_tests/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.56-green?style=flat-square&logo=playwright)](https://playwright.dev/)
[![pytest](https://img.shields.io/badge/pytest-8.4+-orange?style=flat-square&logo=pytest)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](LICENSE)

UI-автотесты веб-приложения с табличными разделами (заказы, продукты, платежи, документы, скидки, уведомления): структура раздела, пагинация, сортировка и фильтры.

## 🧩 Технические характеристики

*   **Архитектура:** **Page Object + компоненты**. Общий `SectionPage` для всех табличных разделов; пагинатор, сортировка и фильтр — отдельные переиспользуемые компоненты.
*   **Разделы как данные:** каждый раздел описан в `config/sections.py` (колонки с типами, сортируемые колонки, фильтры). Тесты параметризуются по этим описаниям — новый раздел добавляется записью в конфиге, без копирования кода.
*   **Точные проверки:** фильтр проверяется по содержимому каждой строки результата, а не по «таблица не пуста»; размер страницы — по фактическому числу строк; сортировка — по разобранным значениям (числа с неразрывными пробелами, даты со временем, ё/е).
*   **Честные пропуски:** если данных для проверки нет, тест помечается `skipped` с причиной, а не проходит «зелёным».
*   **Одна авторизация на сессию:** вход через SSO выполняется один раз, состояние браузера переиспользуется всеми тестами.
*   **Стабильность:** только авто-ожидания Playwright (`expect`), без `networkidle` и `sleep`.
*   **Отладка:** при падении pytest-playwright сохраняет скриншот и trace (`test-results/`), подробный лог — в `test-results/test_run.log`; чувствительные данные в логах маскируются.
*   **CI:** GitHub Actions — линтер (ruff), офлайн-тесты фреймворка и проверка сборки тестов на каждый push и PR.
*   **Стек:** Python 3.13, `pytest`, `playwright`, `pytest-playwright`, `pydantic-settings`, `Allure`.

> 🔒 **Примечание для портфолио:** код представляет собой демонстрационную версию. Реальные адреса стендов, учётные данные, названия внутренних UI-компонентов, маршруты и бизнес-данные заменены на обобщённые плейсхолдеры для соблюдения NDA корпоративного клиента.

## 📁 Структура

```
integration_tests/
├── config/        # settings (.env), constants, sections — описания разделов
├── pages/         # Page Objects: BasePage, LoginPage, SectionPage
├── components/    # paginator, table_sorting, table_filter
├── helpers/       # разбор значений ячеек, мягкие проверки
├── tests/         # UI-тесты: layout, pagination, sorting, filtering (требуют стенд)
├── unit_tests/    # офлайн-тесты самого фреймворка (запускаются в CI)
└── utils/         # логгер с маскированием
```

## 🚀 Как запустить

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r integration_tests/requirements.txt
playwright install chromium

cp integration_tests/.env.example integration_tests/.env   # заполнить BASE_URL, TEST_USERNAME, TEST_PASSWORD

pytest                                   # все UI-тесты
pytest -m smoke                          # только smoke
pytest -m sorting -k orders              # сортировка в разделе «Заказы»
pytest -n 4                              # параллельно (pytest-xdist)
pytest --headed --browser firefox        # с окном браузера, в другом браузере
```

Отчёт Allure (результаты пишутся в `allure-results/`):

```bash
allure serve allure-results
```

Trace упавшего теста:

```bash
playwright show-trace test-results/<тест>/trace.zip
```

### Проверки без доступа к стенду

```bash
ruff check --config integration_tests/ruff.toml integration_tests
pytest integration_tests/unit_tests      # парсинг ячеек, сортировка, описания разделов, маскирование
pytest --collect-only -q                 # все тесты собираются
```

## 📄 Документация и аналитика
Примеры оформления тест-кейсов, баг-репортов и тест-планов доступны в отдельном репозитории-портфолио:
➡️ [test-artifacts-examples](https://github.com/KAKnetuz/test-artifacts-examples)
