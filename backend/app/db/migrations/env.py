from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

import app.db.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base

config = context.config
migration_url = settings.database_url.replace("+asyncpg", "+psycopg").replace("+aiosqlite", "")
config.set_main_option("sqlalchemy.url", migration_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

MIGRATION_MANAGED_INDEXES = {
    "ix_chunks_embedding_cosine_ivfflat",
    "ix_chunks_workspace_version_ordinal",
    "ix_document_versions_document_version_desc",
    "ix_documents_workspace_status_updated",
    "ix_ingestion_jobs_workspace_status_updated",
}


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    if reflected and compare_to is None and type_ == "index" and name in MIGRATION_MANAGED_INDEXES:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
