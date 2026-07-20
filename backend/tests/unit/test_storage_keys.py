from uuid import uuid4

import pytest

from app.integrations.storage.keys import document_object_key, safe_object_name
from app.integrations.storage.local import LocalObjectStorage


def test_safe_object_name_strips_user_paths():
    assert safe_object_name("../../secret.txt") == "secret.txt"
    assert safe_object_name("nested\\windows\\report final.pdf") == "report-final.pdf"


def test_document_object_key_is_scoped_to_workspace_document_and_version():
    workspace_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()

    key = document_object_key(
        group="quarantine",
        workspace_id=workspace_id,
        document_id=document_id,
        version_id=version_id,
        filename="../../secret.txt",
        unique=False,
    )

    assert key == (
        f"quarantine/workspaces/{workspace_id}/documents/{document_id}/"
        f"versions/{version_id}/secret.txt"
    )


def test_document_object_key_rejects_unknown_group():
    with pytest.raises(ValueError):
        document_object_key(
            group="private",
            workspace_id=uuid4(),
            document_id=uuid4(),
            version_id=uuid4(),
            filename="x.txt",
        )


@pytest.mark.asyncio
async def test_local_storage_rejects_traversal_key(tmp_path):
    storage = LocalObjectStorage(tmp_path)

    with pytest.raises(ValueError):
        await storage.put("../outside.txt", b"secret", "text/plain")
