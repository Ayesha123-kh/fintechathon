"""Dragonfly (Redis protocol) client used for sessions, rate limits, presence and chat fan-out."""

from redis.asyncio import Redis

from app.core.config import settings

redis: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Fixed-window limiter. Returns True when the call is allowed."""
    full = f"rl:{key}"
    count = await redis.incr(full)
    if count == 1:
        await redis.expire(full, window_seconds)
    return count <= limit


def chat_channel(user_id: str) -> str:
    return f"chat:{user_id}"


def presence_key(user_id: str) -> str:
    return f"online:{user_id}"
