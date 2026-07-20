from __future__ import annotations

from uuid import UUID, uuid4


def safe_object_name(filename: str) -> str:
    cleaned = filename.replace("\\", "/").split("/")[-1].strip().strip(".")
    allowed = [char if char.isalnum() or char in {"-", "_", "."} else "-" for char in cleaned]
    result = "".join(allowed).strip("-")
    return result[:160] or "upload"


def document_object_key(
    *,
    group: str,
    workspace_id: UUID,
    document_id: UUID,
    version_id: UUID,
    filename: str,
    unique: bool = True,
) -> str:
    if group not in {"quarantine", "source", "parsed", "reports"}:
        raise ValueError("Unsupported object group")
    prefix = f"{group}/workspaces/{workspace_id}/documents/{document_id}/versions/{version_id}"
    object_name = safe_object_name(filename)
    if unique:
        object_name = f"{uuid4()}-{object_name}"
    return f"{prefix}/{object_name}"
