"""Dragonfly (Redis protocol) client used for sessions, rate limits, presence and chat fan-out."""

from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.config import settings

redis: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Fixed-window limiter. Returns True when the call is allowed."""
    full = f"rl:{key}"
    async with redis.pipeline(transaction=True) as pipe:
        count, ttl = await pipe.incr(full).ttl(full).execute()
    # A new counter, or one whose expiry was lost (e.g. a crash between the two calls), gets one now: a counter
    # without an expiry would lock that key out for good.
    if ttl < 0:
        await redis.expire(full, window_seconds)
    return count <= limit


async def enforce(key: str, limit: int, window_seconds: int, detail: str = "too_many_attempts") -> None:
    """Count one call; past the limit, refuse with 429 and say when to retry."""
    if not await rate_limit(key, limit, window_seconds):
        retry = await redis.ttl(f"rl:{key}")
        raise HTTPException(429, detail, headers={"Retry-After": str(max(retry, 1))})


async def over_limit(key: str, limit: int) -> bool:
    """Whether a counter has already reached its limit, without counting this call (e.g. failed sign-ins)."""
    return int(await redis.get(f"rl:{key}") or 0) >= limit


def chat_channel(user_id: str) -> str:
    return f"chat:{user_id}"


def presence_key(user_id: str) -> str:
    return f"online:{user_id}"
