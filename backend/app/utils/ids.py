from uuid import UUID, uuid4


def new_id() -> UUID:
    return uuid4()


def short_id(value: UUID | None = None) -> str:
    return str(value or uuid4()).split("-")[0]
