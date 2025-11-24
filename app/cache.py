import json
from functools import lru_cache
from typing import Any

import redis

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> redis.Redis:
    # decode_responses to keep everything as str for JSON encoding/decoding
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_json(key: str) -> Any | None:
    raw = get_client().get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def set_json(key: str, value: Any, ex: int | None = None) -> None:
    payload = json.dumps(value)
    get_client().set(key, payload, ex=ex)


def delete(key: str) -> None:
    get_client().delete(key)
