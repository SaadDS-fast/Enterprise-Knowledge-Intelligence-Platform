from __future__ import annotations

import re
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentPrincipal
from app.db.models import Membership, Organization, User, Workspace
from app.db.session import get_db
from app.exceptions.base import AppError, ConflictError
from app.exceptions.codes import ErrorCode
from app.models.schemas import TokenResponse, UserCreate, UserLogin, UserRead
from app.repositories.users import get_user_by_email
from app.repositories.workspaces import first_membership
from app.security.authentication import create_access_token, hash_password, verify_password

router = APIRouter()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "workspace")[:80]


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: UserCreate, session: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    if await get_user_by_email(session, payload.email):
        raise ConflictError("An account with this email already exists")
    suffix = str(uuid4()).split("-")[0]
    organization = Organization(
        name=payload.organization_name, slug=f"{slugify(payload.organization_name)}-{suffix}"
    )
    session.add(organization)
    await session.flush()
    workspace = Workspace(
        organization_id=organization.id,
        name=payload.workspace_name,
        slug=slugify(payload.workspace_name),
    )
    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add_all([workspace, user])
    await session.flush()
    session.add(Membership(user_id=user.id, workspace_id=workspace.id, role="owner"))
    await session.commit()
    await session.refresh(user)
    token = create_access_token(user.id, workspace.id)
    return TokenResponse(
        access_token=token,
        expires_in=30 * 60,
        user=UserRead.model_validate(user),
        workspace_id=workspace.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin, session: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    user = await get_user_by_email(session, str(payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(ErrorCode.AUTHENTICATION_FAILED, "Incorrect email or password", 401)
    membership = await first_membership(session, user.id)
    if not membership:
        raise AppError(ErrorCode.FORBIDDEN, "The account has no workspace membership", 403)
    token = create_access_token(user.id, membership.workspace_id)
    return TokenResponse(
        access_token=token,
        expires_in=30 * 60,
        user=UserRead.model_validate(user),
        workspace_id=membership.workspace_id,
    )


@router.get("/me", response_model=UserRead)
async def me(principal: CurrentPrincipal) -> UserRead:
    return UserRead.model_validate(principal.user)
