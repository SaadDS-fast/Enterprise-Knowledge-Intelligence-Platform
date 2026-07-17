from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator


class EmbeddingVector(TypeDecorator):
    cache_ok = True
    impl = JSON

    def __init__(self, dimensions: int = 384) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(
            Vector(self.dimensions) if dialect.name == "postgresql" else JSON()
        )
