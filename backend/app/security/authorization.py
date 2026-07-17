from app.db.models.role import RoleName
from app.exceptions.base import ForbiddenError

ROLE_LEVEL = {
    RoleName.VIEWER.value: 10,
    RoleName.EDITOR.value: 20,
    RoleName.ADMIN.value: 30,
    RoleName.OWNER.value: 40,
}


def require_role(actual: str, minimum: RoleName) -> None:
    if ROLE_LEVEL.get(actual, 0) < ROLE_LEVEL[minimum.value]:
        raise ForbiddenError(f"This action requires the {minimum.value} role or higher")


def can_manage_documents(role: str) -> bool:
    return ROLE_LEVEL.get(role, 0) >= ROLE_LEVEL[RoleName.EDITOR.value]
