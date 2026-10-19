import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import cache
from app.core.config import settings
from app.core.deps import client_ip


class FakeRedis:
    """Just the commands the limiter uses."""

    def __init__(self):
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self, transaction=True):
        return FakePipeline(self)

    async def expire(self, key, seconds):
        self.ttls[key] = seconds

    async def ttl(self, key):
        return -2 if key not in self.values else self.ttls.get(key, -1)

    async def get(self, key):
        return self.values.get(key)


class FakePipeline:
    def __init__(self, r):
        self.r, self.ops = r, []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def incr(self, key):
        self.ops.append(("incr", key))
        return self

    def ttl(self, key):
        self.ops.append(("ttl", key))
        return self

    async def execute(self):
        out = []
        for op, key in self.ops:
            if op == "incr":
                self.r.values[key] = self.r.values.get(key, 0) + 1
                out.append(self.r.values[key])
            else:
                out.append(-2 if key not in self.r.values else self.r.ttls.get(key, -1))
        return out


@pytest.fixture
def fake(monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr(cache, "redis", r)
    return r


async def test_calls_past_the_limit_are_refused(fake):
    assert [await cache.rate_limit("k", 3, 60) for _ in range(4)] == [True, True, True, False]
    assert fake.ttls["rl:k"] == 60


async def test_a_counter_that_lost_its_expiry_gets_one_again(fake):
    fake.values["rl:k"] = 50  # e.g. the process died between INCR and EXPIRE
    assert await cache.rate_limit("k", 3, 60) is False
    assert fake.ttls["rl:k"] == 60  # so it can't lock the key out for good


async def test_enforce_answers_429_with_retry_after(fake):
    await cache.enforce("k", 1, 30)
    with pytest.raises(HTTPException) as err:
        await cache.enforce("k", 1, 30)
    assert err.value.status_code == 429 and err.value.headers == {"Retry-After": "30"}


async def test_over_limit_reads_without_counting(fake):
    for _ in range(2):
        await cache.rate_limit("fails", 2, 60)
    assert await cache.over_limit("fails", 2) and fake.values["rl:fails"] == 2


def request(xff: str | None, peer: str = "10.0.0.5") -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_client_ip_ignores_addresses_a_client_can_forge(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    # The client sent "6.6.6.6, 7.7.7.7"; the edge appended the real address.
    assert client_ip(request("6.6.6.6, 7.7.7.7, 203.0.113.9")) == "203.0.113.9"
    assert client_ip(request(None)) == "10.0.0.5"


def test_client_ip_with_two_proxies_in_front(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    assert client_ip(request("6.6.6.6, 203.0.113.9, 198.51.100.1")) == "203.0.113.9"
    assert client_ip(request("203.0.113.9")) == "10.0.0.5"  # fewer entries than proxies: not trustworthy
