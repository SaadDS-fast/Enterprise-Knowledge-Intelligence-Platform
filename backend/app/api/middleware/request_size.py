from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.exceptions.codes import ErrorCode


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        try:
            parsed_content_length = int(content_length) if content_length else 0
        except ValueError:
            parsed_content_length = settings.max_request_body_bytes + 1
        if parsed_content_length > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": ErrorCode.REQUEST_TOO_LARGE.value,
                        "message": "Request body exceeds configured size limit",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )
        return await call_next(request)
