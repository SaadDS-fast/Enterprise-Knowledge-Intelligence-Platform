from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings
from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode
from app.utils.time import utc_now

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(
    user_id: UUID, workspace_id: UUID, extra: dict[str, Any] | None = None
) -> str:
    now = utc_now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except InvalidTokenError as exc:
        raise AppError(
            ErrorCode.AUTHENTICATION_FAILED, "Invalid or expired access token", 401
        ) from exc
    if payload.get("type") != "access":
        raise AppError(ErrorCode.AUTHENTICATION_FAILED, "Invalid token type", 401)
    return payload
