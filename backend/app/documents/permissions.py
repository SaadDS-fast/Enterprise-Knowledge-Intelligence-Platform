from app.security.authorization import can_manage_documents


def can_read_document(role: str) -> bool:
    return role in {"viewer", "editor", "admin", "owner"}


def can_write_document(role: str) -> bool:
    return can_manage_documents(role)
