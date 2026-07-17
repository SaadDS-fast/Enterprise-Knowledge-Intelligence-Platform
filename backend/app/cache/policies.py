from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CachePolicy:
    ttl_seconds: int
    cache_empty: bool = False


SEARCH_POLICY = CachePolicy(120)
PERMISSION_POLICY = CachePolicy(60)
