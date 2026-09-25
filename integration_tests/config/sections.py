"""
Разделы приложения, описанные как данные.

Каждый раздел — это таблица с колонками, сортировкой и фильтрами. Тесты
параметризуются по этим описаниям, поэтому новый раздел добавляется записью
здесь, без копирования тестового кода.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from integration_tests.config.constants import TOOLBAR_ICONS


class ValueType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"


@dataclass(frozen=True)
class Column:
    title: str
    # Ключ CDK-колонки: заголовок ищется как th.cdk-column-<key>; без ключа — по тексту
    key: str | None = None
    type: ValueType = ValueType.TEXT

    @property
    def header_selector(self) -> str:
        return f"th.cdk-column-{self.key}" if self.key else f"th:has-text('{self.title}')"


@dataclass(frozen=True)
class CheckboxFilter:
    column: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class DateFilter:
    column: str
    # True — в колонке только прошедшие события, будущий период обязан быть пустым.
    # Для сроков действия будущие даты — нормальные данные, проверка не применяется.
    future_is_empty: bool = True


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    table: str
    columns: tuple[Column, ...]
    menu: str | None = None
    tab: str | None = None
    nav_selector: str | None = None
    url_pattern: str | None = None
    icons: tuple[str, ...] = ("filter", "settings", "fullscreen")
    sortable: tuple[str, ...] = ()
    text_filters: tuple[str, ...] = ()
    checkbox_filters: tuple[CheckboxFilter, ...] = ()
    date_filters: tuple[DateFilter, ...] = ()
    paginated: bool = True
    _by_title: dict = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_title", {c.title: c for c in self.columns})

    def column(self, title: str) -> Column:
        try:
            return self._by_title[title]
        except KeyError:
            raise KeyError(f"В разделе '{self.id}' нет колонки '{title}'") from None

    @property
    def icon_selectors(self) -> dict[str, str]:
        return {name: TOOLBAR_ICONS[name] for name in self.icons}


T, N, D = ValueType.TEXT, ValueType.NUMBER, ValueType.DATE
ALL_ICONS = ("export", "filter", "settings", "fullscreen")

_DOCUMENT_COLUMNS = (
    Column("No."),
    Column("Наименование"),
    Column("Сумма", type=N),
    Column("Сумма с НДС", type=N),
    Column("Провайдер"),
    Column("Покупатель"),
    Column("ИНН"),
    Column("КПП"),
    Column("Заказ"),
    Column("Транзакция"),
)

SECTIONS: tuple[Section, ...] = (
    Section(
        id="orders",
        title="Заказы",
        menu="Заказы",
        url_pattern=r".*/orders",
        table="table.cdk-table",
        icons=ALL_ICONS,
        columns=(
            Column("ID", "id", N),
            Column("Внешний номер", "external_number"),
            Column("Провайдер", "seller_name"),
            Column("Покупатель", "buyer_name"),
            Column("Наименование услуги", "offer_name"),
            Column("Сумма", "price", N),
            Column("НДС", "tax", N),
            Column("Статус", "status"),
            Column("Статус оплаты", "status_pay"),
            Column("Дата создания", "date", D),
            Column("Дата реализации", "realize_date", D),
            Column("Срок действия до", "offer_valid_until", D),
        ),
        sortable=("Внешний номер", "Дата создания", "Дата реализации", "Срок действия до"),
        text_filters=("ID", "Внешний номер", "Провайдер", "Покупатель", "Наименование услуги"),
        checkbox_filters=(
            CheckboxFilter("Статус", ("Новый", "Отменён", "Использован")),
            CheckboxFilter("Статус оплаты", ("Оплачен", "Не оплачен", "Не требует")),
        ),
        date_filters=(
            DateFilter("Дата создания"),
            DateFilter("Дата реализации"),
            DateFilter("Срок действия до", future_is_empty=False),
        ),
    ),
    Section(
        id="offers",
        title="Продукты → Все предложения",
        menu="Продукты",
        tab="Все предложения",
        url_pattern=r".*/products/offer-list",
        table="app-all-offers-table table.cdk-table",
        columns=(
            Column("ID", "id", N),
            Column("Наименование", "name"),
            Column("Продукт", "product_name"),
            Column("Провайдер", "contragent_name"),
            Column("Платформа", "platform"),
            Column("Тип", "type"),
            Column("Цена", "price", N),
            Column("НДС", "tax", N),
            Column("Статус", "status"),
            Column("Создан", "created_date", D),
            Column("Срок действия", "valid_until", D),
            Column("Создано заказов"),
        ),
        sortable=("Создан", "Срок действия"),
        text_filters=("ID", "Наименование", "Продукт", "Провайдер", "Платформа"),
        checkbox_filters=(
            CheckboxFilter("Статус", ("Активен", "Архивный", "Черновик")),
            CheckboxFilter("Тип", ("Разовая услуга", "Подписной пакет", "Пакет")),
        ),
        date_filters=(DateFilter("Создан"),),
    ),
    Section(
        id="products",
        title="Продукты",
        menu="Продукты",
        tab="Продукты",
        url_pattern=r".*/products/product-list",
        table="app-products-table table.cdk-table",
        columns=(
            Column("ID", "id", N),
            Column("Наименование", "name"),
            Column("Описание", "description"),
            Column("Кол-во предложений", "offers_number", N),
            Column("Статус", "status"),
            Column("Дата создания", "created_date", D),
        ),
        sortable=("Дата создания",),
        text_filters=("ID", "Наименование"),
        checkbox_filters=(CheckboxFilter("Статус", ("Активен", "Архивный", "Черновик")),),
        date_filters=(DateFilter("Дата создания"),),
    ),
    Section(
        id="payments",
        title="Финансы → Платежи",
        menu="Финансы",
        tab="Платежи",
        url_pattern=r".*/finance/payments",
        table="app-payments-table table.cdk-table",
        icons=ALL_ICONS,
        columns=(
            Column("№", "index", N),
            Column("Дата создания", "creation_date", D),
            Column("Дата создания п/п", "payment_date", D),
            Column("Дата исполнения п/п", "real_payment_date", D),
            Column("Номер п/п", "payment_number"),
            Column("Ид. платежа"),
            Column("ИНН", "client_inn"),
            Column("КПП", "client_kpp"),
            Column("TIN", "client_tin"),
            Column("ЛС", "client_account"),
            Column("Контрагент", "contragent_name"),
            Column("Сумма", "sum", N),
            Column("Тип платежа", "pay_category"),
            Column("Способ оплаты", "paid_by_type"),
            Column("Статус платежа", "status"),
        ),
        sortable=("Дата создания", "Дата создания п/п", "Дата исполнения п/п"),
        text_filters=("ИНН", "КПП", "TIN", "ЛС", "Контрагент", "Сумма"),
        checkbox_filters=(
            CheckboxFilter("Тип платежа", ("1C", "Ручное")),
            CheckboxFilter("Способ оплаты", ("Эквайринг", "Банк")),
            CheckboxFilter("Статус платежа", ("Успешно", "Ошибка")),
        ),
        date_filters=(
            DateFilter("Дата создания"),
            DateFilter("Дата создания п/п"),
            DateFilter("Дата исполнения п/п"),
        ),
    ),
    Section(
        id="withdrawals",
        title="Финансы → Вывод ДС",
        menu="Финансы",
        tab="Вывод ДС",
        url_pattern=r".*/finance/withdrawals",
        table="app-withdrawals-table table.cdk-table",
        icons=ALL_ICONS,
        columns=(
            Column("№", "id", N),
            Column("Дата создания", "date", D),
            Column("ИНН", "inn"),
            Column("КПП", "kpp"),
            Column("TIN", "tin"),
            Column("ЛС", "account"),
            Column("Контрагент", "buyer_short_name"),
            Column("Сумма", "price", N),
            Column("Создал", "created_by"),
            Column("Дата исполнения", "realize_date", D),
            Column("Статус платежа", "status"),
        ),
        sortable=("Дата создания", "Дата исполнения"),
        text_filters=("ИНН", "КПП", "ЛС", "Контрагент", "Создал", "Сумма"),
        checkbox_filters=(CheckboxFilter("Статус платежа", ("Новый", "Исполнен", "Отменен")),),
        date_filters=(DateFilter("Дата создания"), DateFilter("Дата исполнения")),
    ),
    Section(
        id="upd",
        title="Документы → УПД",
        menu="Документы",
        tab="УПД",
        table="app-bills-table table.cdk-table",
        columns=(*_DOCUMENT_COLUMNS, Column("Дата", type=D)),
        sortable=("Дата",),
    ),
    Section(
        id="ukd",
        title="Документы → УКД",
        menu="Документы",
        tab="УКД",
        table="app-bill-corrections-table table.cdk-table",
        columns=(*_DOCUMENT_COLUMNS, Column("УПД"), Column("Дата", type=D)),
        sortable=("Дата",),
    ),
    Section(
        id="invoices",
        title="Документы → Счета на оплату",
        menu="Документы",
        tab="Счета на оплату",
        url_pattern=r".*/documents/invoices",
        table="app-invoices-table table.cdk-table",
        columns=(
            *_DOCUMENT_COLUMNS,
            Column("Статус"),
            Column("Дата", "date", D),
            Column("Дата оплаты", type=D),
        ),
        sortable=("Дата",),
    ),
    Section(
        id="statements",
        title="Документы → Заявления",
        menu="Документы",
        tab="Заявления",
        table="app-agreements-table table.cdk-table",
        columns=(
            Column("No.", "id", N),
            Column("Наименование", "name"),
            Column("Провайдер", "provider_name"),
            Column("Покупатель", "buyer_name"),
            Column("ИНН", "inn"),
            Column("КПП", "kpp"),
            Column("Транзакция", "transaction_id"),
            Column("Сумма", "pure_amount", N),
            Column("Сумма с НДС", "obligations_amount", N),
            Column("Дата", "date", D),
        ),
        sortable=("Наименование", "Покупатель", "Сумма", "Дата"),
    ),
    Section(
        id="discounts",
        title="Скидки",
        menu="Скидки",
        url_pattern=r".*/discounts",
        table="app-discount-table table.cdk-table",
        columns=(
            Column("No."),
            Column("Наименование"),
            Column("Размер"),
            Column("Статус"),
            Column("Активна с", "valid_from", D),
            Column("Активна по", "valid_until", D),
            Column("Доступно использ"),
            Column("Создал"),
            Column("Промокод"),
            Column("Персональная"),
        ),
        sortable=("Активна с", "Активна по"),
    ),
    Section(
        id="notifications",
        title="Уведомления",
        nav_selector='span[nztype="bell"]',
        url_pattern=r".*/notifications",
        table="app-notifications-table table.cdk-table",
        columns=(
            Column("No.", type=N),
            Column("Дата", type=D),
            Column("Тема уведомления"),
        ),
        sortable=("No.", "Дата", "Тема уведомления"),
    ),
)

SECTIONS_BY_ID: dict[str, Section] = {s.id: s for s in SECTIONS}
