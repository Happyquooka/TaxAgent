from __future__ import annotations

from typing import Any

import redis

from app.core.settings import get_settings


def get_redis_client() -> Any | None:
    settings = get_settings()
    try:
        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None
