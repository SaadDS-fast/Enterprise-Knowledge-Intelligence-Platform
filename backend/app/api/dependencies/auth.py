from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db
from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode
from app.security.authentication import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user: User
    default_workspace_id: UUID


async def get_current_principal(
    token: Annotated[str, Depends(oauth2_scheme)], session: Annotated[AsyncSession, Depends(get_db)]
) -> AuthenticatedPrincipal:
    payload = decode_access_token(token)
    try:
        user_id = UUID(payload["sub"])
        workspace_id = UUID(payload["workspace_id"])
    except (KeyError, ValueError) as exc:
        raise AppError(ErrorCode.AUTHENTICATION_FAILED, "Malformed access token", 401) from exc
    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise AppError(ErrorCode.AUTHENTICATION_FAILED, "User is inactive or missing", 401)
    return AuthenticatedPrincipal(user=user, default_workspace_id=workspace_id)


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
