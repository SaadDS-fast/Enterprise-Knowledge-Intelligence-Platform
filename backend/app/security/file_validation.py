from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode


@dataclass(frozen=True, slots=True)
class ValidatedFile:
    filename: str
    extension: str
    mime_type: str
    size_bytes: int


MAGIC_PREFIXES = {".pdf": (b"%PDF-",), ".docx": (b"PK\x03\x04",)}
EXTENSION_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".html": {"text/html", "text/plain"},
    ".csv": {"text/csv", "text/plain"},
    ".py": {"text/x-python", "text/plain", "application/octet-stream"},
    ".js": {"application/javascript", "text/javascript", "text/plain", "application/octet-stream"},
    ".ts": {"application/javascript", "text/javascript", "text/plain", "application/octet-stream"},
    ".java": {"text/plain", "application/octet-stream"},
    ".cpp": {"text/plain", "application/octet-stream"},
}


def validate_file(filename: str | None, mime_type: str | None, data: bytes) -> ValidatedFile:
    safe_name = Path((filename or "upload").replace("\\", "/")).name
    extension = Path(safe_name).suffix.lower()
    if extension not in settings.allowed_file_extensions:
        raise AppError(
            ErrorCode.VALIDATION_FAILED, f"Unsupported file extension: {extension or 'none'}", 415
        )
    if not data:
        raise AppError(ErrorCode.VALIDATION_FAILED, "The uploaded file is empty", 400)
    if len(data) > settings.max_upload_bytes:
        raise AppError(
            ErrorCode.VALIDATION_FAILED, "The uploaded file exceeds the configured size limit", 413
        )
    normalized_mime = (mime_type or "application/octet-stream").split(";")[0].strip().lower()
    if normalized_mime not in settings.allowed_mime_types:
        raise AppError(
            ErrorCode.VALIDATION_FAILED, f"Unsupported MIME type: {normalized_mime}", 415
        )
    expected_mimes = EXTENSION_MIME_TYPES.get(extension, set())
    if expected_mimes and normalized_mime not in expected_mimes:
        raise AppError(
            ErrorCode.VALIDATION_FAILED,
            "File MIME type does not match its extension",
            415,
        )
    signatures = MAGIC_PREFIXES.get(extension)
    if signatures and not any(data.startswith(prefix) for prefix in signatures):
        raise AppError(
            ErrorCode.VALIDATION_FAILED, "File content does not match its extension", 415
        )
    if b"\x00" in data[:4096] and extension not in {".pdf", ".docx"}:
        raise AppError(ErrorCode.VALIDATION_FAILED, "Unexpected binary content", 415)
    return ValidatedFile(safe_name, extension, normalized_mime, len(data))
