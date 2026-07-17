from typing import Annotated

from fastapi import Depends, Request

from app.security.rate_limiting import rate_limiter


async def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    await rate_limiter.check(f"{client}:{request.url.path}")


RateLimited = Annotated[None, Depends(enforce_rate_limit)]
