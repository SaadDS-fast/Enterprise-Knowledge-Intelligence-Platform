from types import SimpleNamespace
from uuid import UUID

import pytest

from app.core.config import settings
from app.db.models.role import RoleName
from app.models.schemas import AnswerPassportReference
from app.passport.issuance import IssuanceContext, PassportIssuanceCoordinator
from app.passport.persistence import PassportPersistenceStatus
from app.rag.response_state import PrimaryResponseState
from app.services import search_service
from tests.unit.test_passport_issuance import ISSUED_AT, TestSigner, projection, response_for


class Persistence:
    def __init__(self, status: PassportPersistenceStatus) -> None:
        self.status = status

    async def persist_issued(self, *args: object, **kwargs: object) -> SimpleNamespace:
        del args, kwargs
        record = (
            SimpleNamespace(
                passport_id="urn:uuid:00000000-0000-0000-0000-000000000042",
                schema_version="vap-1",
            )
            if self.status
            in {PassportPersistenceStatus.PERSISTED, PassportPersistenceStatus.DUPLICATE}
            else None
        )
        return SimpleNamespace(status=self.status, record=record)


async def _run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    primary: PrimaryResponseState = PrimaryResponseState.SUPPORTED,
    persistence_status: PassportPersistenceStatus = PassportPersistenceStatus.PERSISTED,
    role: RoleName = RoleName.EDITOR,
):
    organization_id = UUID(int=90)
    workspace_id = UUID(int=50)
    response = response_for(primary)

    async def finalized(*args: object, **kwargs: object):
        del args, kwargs
        return response

    async def projected(*args: object, **kwargs: object):
        del args, kwargs
        return projection(tenant_id=str(organization_id), workspace_id=str(workspace_id))

    monkeypatch.setattr(search_service, "_search_and_answer", finalized)
    monkeypatch.setattr(search_service, "project_search_response", projected)
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    return await search_service.search_and_answer(
        object(),  # type: ignore[arg-type]
        workspace_id=workspace_id,
        query="finalized answer",
        passport_coordinator=PassportIssuanceCoordinator(
            enabled=True, signer=TestSigner(), clock=lambda: ISSUED_AT
        ),
        passport_context=IssuanceContext(),
        passport_persistence_coordinator=Persistence(persistence_status),  # type: ignore[arg-type]
        passport_actor_role=role,
    )


@pytest.mark.asyncio
async def test_successful_persistence_adds_only_minimal_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = await _run(monkeypatch)
    assert response.passport_reference is not None
    assert response.passport_reference.model_dump() == {
        "passport_id": "urn:uuid:00000000-0000-0000-0000-000000000042",
        "schema_version": "vap-1",
        "metadata_available": True,
        "export_available": True,
    }
    wire = response.model_dump(mode="json")
    assert "manifest" not in wire and "signature" not in wire


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        PassportPersistenceStatus.NOT_PERSISTED,
        PassportPersistenceStatus.FAILED,
    ],
)
async def test_unpersisted_or_failed_persistence_omits_reference(
    monkeypatch: pytest.MonkeyPatch, status: PassportPersistenceStatus
) -> None:
    assert (await _run(monkeypatch, persistence_status=status)).passport_reference is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary",
    [
        PrimaryResponseState.CONFLICTING_EVIDENCE,
        PrimaryResponseState.PROCESSING_FAILED,
        PrimaryResponseState.INSUFFICIENT_EVIDENCE,
    ],
)
async def test_non_supported_terminal_states_omit_reference(
    monkeypatch: pytest.MonkeyPatch, primary: PrimaryResponseState
) -> None:
    assert (await _run(monkeypatch, primary=primary)).passport_reference is None


@pytest.mark.asyncio
async def test_reference_export_hint_is_role_aware_but_not_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = await _run(monkeypatch, role=RoleName.VIEWER)
    assert response.passport_reference is not None
    assert response.passport_reference.metadata_available is True
    assert response.passport_reference.export_available is False


def test_response_schema_strips_reference_from_non_supported_state() -> None:
    response = response_for(PrimaryResponseState.CONFLICTING_EVIDENCE)
    response.passport_reference = AnswerPassportReference(
        passport_id="urn:uuid:00000000-0000-0000-0000-000000000042",
        schema_version="vap-1",
        metadata_available=True,
        export_available=True,
    )
    rebuilt = type(response).model_validate(response.model_dump())
    assert rebuilt.passport_reference is None
