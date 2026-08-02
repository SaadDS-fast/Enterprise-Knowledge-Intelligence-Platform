from __future__ import annotations

from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.answer_passport import AnswerPassport
from app.db.models.workspace import Workspace


class PassportPersistenceCollision(ValueError):
    pass


class AnswerPassportRepository(Protocol):
    async def scope_exists(self, organization_id: UUID, workspace_id: UUID) -> bool: ...

    async def persist(self, record: AnswerPassport) -> tuple[AnswerPassport, bool]: ...

    async def get_scoped(
        self, passport_id: str, organization_id: UUID, workspace_id: UUID
    ) -> AnswerPassport | None: ...


class SQLAlchemyAnswerPassportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def scope_exists(self, organization_id: UUID, workspace_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(Workspace.id).where(
                    Workspace.id == workspace_id,
                    Workspace.organization_id == organization_id,
                )
            )
        ) is not None

    async def _by_idempotency(
        self, key: str, organization_id: UUID, workspace_id: UUID
    ) -> AnswerPassport | None:
        return cast(
            AnswerPassport | None,
            await self.session.scalar(
                select(AnswerPassport).where(
                    AnswerPassport.idempotency_key == key,
                    AnswerPassport.organization_id == organization_id,
                    AnswerPassport.workspace_id == workspace_id,
                )
            ),
        )

    async def persist(self, record: AnswerPassport) -> tuple[AnswerPassport, bool]:
        existing = await self._by_idempotency(
            record.idempotency_key, record.organization_id, record.workspace_id
        )
        if existing is not None:
            if existing.artifact_checksum != record.artifact_checksum:
                raise PassportPersistenceCollision("passport_persistence_collision")
            return existing, False
        try:
            async with self.session.begin_nested():
                self.session.add(record)
                await self.session.flush()
            return record, True
        except IntegrityError as exc:
            existing = await self._by_idempotency(
                record.idempotency_key, record.organization_id, record.workspace_id
            )
            if existing is not None and existing.artifact_checksum == record.artifact_checksum:
                return existing, False
            raise PassportPersistenceCollision("passport_persistence_collision") from exc

    async def get_scoped(
        self, passport_id: str, organization_id: UUID, workspace_id: UUID
    ) -> AnswerPassport | None:
        return cast(
            AnswerPassport | None,
            await self.session.scalar(
                select(AnswerPassport).where(
                    AnswerPassport.passport_id == passport_id,
                    AnswerPassport.organization_id == organization_id,
                    AnswerPassport.workspace_id == workspace_id,
                )
            ),
        )
