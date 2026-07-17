from uuid import UUID

from sqlalchemy import Select


def workspace_scope(statement: Select, model: type, workspace_id: UUID) -> Select:
    if not hasattr(model, "workspace_id"):
        raise TypeError(f"{model.__name__} is not workspace-scoped")
    return statement.where(model.workspace_id == workspace_id)
