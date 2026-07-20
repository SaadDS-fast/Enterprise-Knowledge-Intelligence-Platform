from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RETRY_PENDING = "retry_pending"
    DISPATCH_FAILED = "dispatch_failed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionStage(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    QUARANTINED = "quarantined"
    SCANNING = "scanning"
    PARSING = "parsing"
    NORMALIZING = "normalizing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
