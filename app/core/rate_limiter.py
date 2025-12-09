"""Rate limiting using Redis sliding window."""
import time
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

redis_client: redis.Redis | None = None


def init_redis() -> redis.Redis:
    """Initialize Redis client."""
    global redis_client
    redis_client = redis.from_url(str(settings.redis_url), decode_responses=True)
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    if redis_client:
        await redis_client.close()


async def check_rate_limit(
    request: Request, identifier: str, limit: int = 5, window: int = 60
) -> None:
    """
    Check rate limit using Redis sliding window.

    Args:
        request: FastAPI request
        identifier: Unique identifier (email or IP)
        limit: Maximum requests per window
        window: Time window in seconds
    """
    if not redis_client:
        logger.warning("Redis client not initialized, skipping rate limit")
        return

    key = f"rate_limit:orders:{identifier}"
    now = time.time()
    window_start = now - window

    try:
        await redis_client.zremrangebyscore(key, 0, window_start)

        count = await redis_client.zcard(key)

        if count >= limit:
            logger.warning(f"Rate limit exceeded for {identifier}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} requests per {window} seconds",
            )

        await redis_client.zadd(key, {str(now): now})
        await redis_client.expire(key, window)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        pass

