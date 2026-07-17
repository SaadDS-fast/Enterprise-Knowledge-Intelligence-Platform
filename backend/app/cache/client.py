from __future__ import annotations

import json

from redis.asyncio import Redis

from app.core.config import settings


class CacheClient:
    def __init__(self) -> None:
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def get_json(self, key: str) -> dict | list | None:
        try:
            value = await self.redis.get(key)
        except Exception:
            return None
        return json.loads(value) if value else None

    async def set_json(self, key: str, value: dict | list, ttl: int | None = None) -> None:
        try:
            await self.redis.set(
                key, json.dumps(value), ex=ttl or settings.cache_default_ttl_seconds
            )
        except Exception:
            return

    async def close(self) -> None:
        await self.redis.aclose()


cache = CacheClient()
