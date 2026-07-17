from enum import StrEnum


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


VALID_TRANSITIONS = {
    DocumentStatus.PENDING: {DocumentStatus.PROCESSING, DocumentStatus.FAILED},
    DocumentStatus.PROCESSING: {DocumentStatus.READY, DocumentStatus.FAILED},
    DocumentStatus.READY: {DocumentStatus.ARCHIVED, DocumentStatus.PROCESSING},
    DocumentStatus.FAILED: {DocumentStatus.PROCESSING, DocumentStatus.ARCHIVED},
    DocumentStatus.ARCHIVED: set(),
}


def can_transition(current: str, target: str) -> bool:
    return DocumentStatus(target) in VALID_TRANSITIONS[DocumentStatus(current)]
