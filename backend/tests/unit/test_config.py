from app.core.config import Settings


def test_local_defaults_are_free():
    settings = Settings(
        _env_file=None, app_env="testing", database_url="sqlite+aiosqlite:///:memory:"
    )
    assert (
        settings.llm_provider.value == "local" and settings.object_storage_provider.value == "local"
    )


def test_chunk_overlap_validation():
    import pytest

    with pytest.raises(ValueError):
        Settings(_env_file=None, chunk_size=200, chunk_overlap=200)


def test_debug_release_environment_is_not_enabled(monkeypatch):
    monkeypatch.setenv("DEBUG", "release")
    settings = Settings(
        _env_file=None, app_env="testing", database_url="sqlite+aiosqlite:///:memory:"
    )
    assert settings.debug is False
