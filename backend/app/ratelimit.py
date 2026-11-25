"""Fixed-window rate limiting with Redis.

For every IP we keep a counter  rl:<bucket>:<ip>  that expires after `window`
seconds. Each request does INCR; if the counter passes the limit we answer 429.
"""
import redis
from fastapi import HTTPException, Request

from . import cache


def client_ip(request: Request) -> str:
    # nginx puts the real visitor address in X-Real-IP
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


def rate_limit(bucket: str, limit: int, window: int = 60):
    def dependency(request: Request):
        key = f"rl:{bucket}:{client_ip(request)}"
        try:
            r = cache.get_client()
            count = r.incr(key)
            if count == 1:
                r.expire(key, window)
            if count > limit:
                retry = max(r.ttl(key), 1)
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Try again in {retry}s.",
                    headers={"Retry-After": str(retry)},
                )
        except redis.RedisError:
            return  # Redis down: don't block users

    return dependency
