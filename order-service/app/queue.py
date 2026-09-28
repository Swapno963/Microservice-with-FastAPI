import json
from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings

RESERVE_QUEUE = "orders:reserve"
RESERVE_RETRY = "orders:reserve:retry"
RELEASE_QUEUE = "orders:release"

_redis: Optional[Redis] = None


def create_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def connect_redis() -> None:
    global _redis
    _redis = create_redis()
    await _redis.ping()


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


def get_redis() -> Optional[Redis]:
    return _redis


def reserve_job(order_id: str, attempt: int = 1) -> str:
    return json.dumps({"order_id": order_id, "attempt": attempt})


async def enqueue_reserve(redis: Redis, order_id: str, attempt: int = 1) -> None:
    await redis.lpush(RESERVE_QUEUE, reserve_job(order_id, attempt))


async def enqueue_reserve_retry(
    redis: Redis, order_id: str, attempt: int, when: float
) -> None:
    await redis.zadd(RESERVE_RETRY, {reserve_job(order_id, attempt): when})


async def enqueue_release(redis: Redis, order_id: str, when: float) -> None:
    await redis.zadd(RELEASE_QUEUE, {order_id: when})


def lock_key(order_id: str) -> str:
    return f"orders:lock:{order_id}"
