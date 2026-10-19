import uuid
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime

from app.core import clock
from app.mcp import user_server


def test_a_pakistani_day_starts_at_midnight_in_karachi():
    assert clock.day_start(date(2026, 10, 20)) == datetime(2026, 10, 19, 19, 0, tzinfo=UTC)


def test_a_month_starts_on_the_first_in_karachi():
    assert clock.month_start(date(2026, 10, 20)) == datetime(2026, 9, 30, 19, 0, tzinfo=UTC)


def test_a_late_night_spend_counts_for_that_pakistani_day():
    spent = datetime(2026, 10, 19, 20, 30, tzinfo=UTC)  # 01:30 on the 20th in Karachi, still the 19th in UTC
    assert clock.day_start(date(2026, 10, 20)) <= spent < clock.day_start(date(2026, 10, 21))


async def test_tool_calls_are_rate_limited_per_person_not_per_key_prefix(monkeypatch):
    # Two people whose member keys start with the same words.
    people = {"amber-anchor-apple-aspen-42-birch-bison-blaze": uuid.uuid4(),
              "amber-anchor-cedar-comet-17-delta-dune-eagle": uuid.uuid4()}
    buckets = []

    async def lookup(key):
        return people.get(key)

    async def limiter(key, limit, window):
        buckets.append(key)
        return True

    @asynccontextmanager
    async def session(user_id, role):
        yield object()

    monkeypatch.setattr(user_server, "user_id_for_member_key", lookup)
    monkeypatch.setattr(user_server, "rate_limit", limiter)
    monkeypatch.setattr(user_server, "scoped_session", session)
    for key, uid in people.items():
        async with user_server.member(key) as (_, got):
            assert got == uid
    assert buckets == [f"mk:{uid}" for uid in people.values()]
