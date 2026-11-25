"""Redis helpers.

Cache-aside pattern for redirects:
  1. look in Redis for  link:<code>
  2. hit  -> redirect immediately (no database query)
  3. miss -> read MySQL, store the result in Redis, then redirect

If Redis is down the app keeps working (just slower): every function here
swallows Redis errors on purpose.
"""
import json
from typing import Optional

import redis

from .config import settings

_client: Optional[redis.Redis] = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


def set_client(client) -> None:
    """Lets the tests plug in a fake Redis."""
    global _client
    _client = client


def _key(code: str) -> str:
    return f"link:{code}"


def get_link(code: str) -> Optional[dict]:
    try:
        raw = get_client().get(_key(code))
        return json.loads(raw) if raw else None
    except redis.RedisError:
        return None


def set_link(code: str, entry: dict, ttl: int) -> None:
    try:
        get_client().set(_key(code), json.dumps(entry), ex=max(1, ttl))
    except redis.RedisError:
        pass


def delete_link(code: str) -> None:
    """Call this whenever a link changes or is deleted, otherwise the cache goes stale."""
    try:
        get_client().delete(_key(code))
    except redis.RedisError:
        pass
