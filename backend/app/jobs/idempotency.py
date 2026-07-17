from app.utils.hashing import hash_text


def idempotency_key(task_type: str, resource_id: object, version: int = 1) -> str:
    return hash_text(f"{task_type}:{resource_id}:v{version}")
