"""Хелперы работы со временем.

Конвенция проекта:
- В БД храним **naive UTC** datetime (без tzinfo, но семантически UTC).
  SQLite не умеет нативно `DateTime(timezone=True)`. Когда переедем на
  PostgreSQL — добавим timezone=True в моделях, и naive_utc_to_db станет
  no-op'ом.
- Все сравнения и timedelta-арифметика — в naive UTC.
- Граница ввода (формы): naive local MSK → aware MSK → aware UTC → naive UTC.
- Граница вывода (шаблоны): naive UTC → aware UTC → aware MSK → strftime
  через jinja-фильтр |local_dt(...).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Локальная TZ приложения. Хочешь поменять регион — меняй здесь.
LOCAL_TZ = ZoneInfo('Europe/Moscow')
UTC = timezone.utc


def now_utc_naive() -> datetime:
    """Текущее UTC-время как naive datetime для записи в БД и сравнений."""
    return datetime.now(UTC).replace(tzinfo=None)


def parse_local_to_utc(local_str: str, fmt: str = '%Y-%m-%dT%H:%M') -> datetime:
    """Парсит строку из формы (naive local MSK) → naive UTC для БД.

    Например '2026-04-30T16:30' (Москва) → datetime(2026,4,30,13,30) UTC.
    """
    naive_local = datetime.strptime(local_str, fmt)
    aware_local = naive_local.replace(tzinfo=LOCAL_TZ)
    aware_utc = aware_local.astimezone(UTC)
    return aware_utc.replace(tzinfo=None)


def utc_to_local(naive_utc: datetime) -> datetime:
    """naive UTC из БД → aware datetime в локальной TZ для отображения."""
    aware_utc = naive_utc.replace(tzinfo=UTC)
    return aware_utc.astimezone(LOCAL_TZ)


def format_local(naive_utc: datetime | None, fmt: str = '%H:%M') -> str:
    """Jinja-фильтр: рендерит naive UTC datetime в локальное время по формату.

    Использование в шаблоне:
        {{ order.pickup_time | local_dt('%d.%m.%Y в %H:%M') }}
    """
    if naive_utc is None:
        return ''
    return utc_to_local(naive_utc).strftime(fmt)
