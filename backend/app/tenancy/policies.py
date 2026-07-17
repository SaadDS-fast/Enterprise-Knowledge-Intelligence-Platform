from app.db.models.role import RoleName
from app.security.authorization import require_role


def require_document_write(role: str) -> None:
    require_role(role, RoleName.EDITOR)


def require_admin(role: str) -> None:
    require_role(role, RoleName.ADMIN)
