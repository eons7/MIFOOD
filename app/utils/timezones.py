"""Хелперы работы со временем. В БД — naive UTC, на вход/выход — local MSK."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo('Europe/Moscow')
UTC = timezone.utc


def now_utc_naive() -> datetime:
    """Текущее UTC-время как naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


def parse_local_to_utc(local_str: str, fmt: str = '%Y-%m-%dT%H:%M') -> datetime:
    """Строка naive local MSK → naive UTC."""
    naive_local = datetime.strptime(local_str, fmt)
    aware_local = naive_local.replace(tzinfo=LOCAL_TZ)
    aware_utc = aware_local.astimezone(UTC)
    return aware_utc.replace(tzinfo=None)


def utc_to_local(naive_utc: datetime) -> datetime:
    """naive UTC → aware datetime в LOCAL_TZ."""
    aware_utc = naive_utc.replace(tzinfo=UTC)
    return aware_utc.astimezone(LOCAL_TZ)


def format_local(naive_utc: datetime | None, fmt: str = '%H:%M') -> str:
    """Jinja-фильтр: naive UTC → строка в LOCAL_TZ по формату fmt."""
    if naive_utc is None:
        return ''
    return utc_to_local(naive_utc).strftime(fmt)
