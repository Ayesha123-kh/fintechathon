"""Pakistan time. "Today", "this month" and a deal's dates are Pakistani calendar days, whatever timezone the
server runs in (containers default to UTC, where a Pakistani day would only start at 05:00)."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

PKT = ZoneInfo("Asia/Karachi")


def today() -> date:
    return datetime.now(PKT).date()


def day_start(day: date | None = None) -> datetime:
    """Midnight in Pakistan at the start of `day` (default: today)."""
    return datetime.combine(day or today(), time.min, PKT)


def month_start(day: date | None = None) -> datetime:
    """Midnight in Pakistan on the first of `day`'s month (default: this month)."""
    return day_start((day or today()).replace(day=1))
