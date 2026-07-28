"""Typed application configuration with secure local-first defaults."""

from __future__ import annotations

import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ProviderType(StrEnum):
    LOCAL = "local"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class LocalInferenceProvider(StrEnum):
    LOCAL = "local"
    DETERMINISTIC = "deterministic"


class StorageProvider(StrEnum):
    LOCAL = "local"
    MINIO = "minio"
    S3 = "s3"
    AZURE = "azure"


class JobExecutionMode(StrEnum):
    INLINE = "inline"
    CELERY = "celery"


class LocalLLMBackend(StrEnum):
    EXTRACTIVE = "extractive"
    OLLAMA = "ollama"


class AgentPlannerProvider(StrEnum):
    DETERMINISTIC = "deterministic"


class WebSearchProvider(StrEnum):
    DISABLED = "disabled"
    DETERMINISTIC = "deterministic"
    SEARXNG = "searxng"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
        validate_default=True,
        enable_decoding=False,
    )
    app_name: str = "Enterprise Knowledge Intelligence Platform"
    app_version: str = "1.0.0"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    frontend_base_url: str = "http://localhost:3000"
    public_api_base_url: str = "http://localhost:8000"
    auto_init_db: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = True
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    request_id_header: str = "X-Request-ID"
    tenant_header: str = "X-Workspace-ID"

    secret_key: SecretStr = SecretStr("development-only-change-me-please")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    password_min_length: int = Field(default=12, ge=8, le=128)

    database_url: str = "sqlite+aiosqlite:///./ekip.db"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_echo: bool = False
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    job_execution_mode: JobExecutionMode = JobExecutionMode.INLINE
    cache_default_ttl_seconds: int = Field(default=300, ge=1, le=86400)

    object_storage_provider: StorageProvider = StorageProvider.LOCAL
    local_storage_path: Path = PROJECT_ROOT / "data" / "storage"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: SecretStr = SecretStr("minioadmin")
    object_storage_bucket: str = "documents"
    object_storage_secure: bool = False
    object_storage_region: str = "us-east-1"
    upload_quarantine_prefix: str = "quarantine"
    upload_approved_prefix: str = "approved"

    max_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1024, le=250 * 1024 * 1024)
    allowed_file_extensions: list[str] = Field(
        default_factory=lambda: [
            ".pdf",
            ".docx",
            ".txt",
            ".md",
            ".html",
            ".csv",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
        ]
    )
    allowed_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
            "text/html",
            "text/csv",
            "text/x-python",
            "application/javascript",
            "text/javascript",
            "application/octet-stream",
        ]
    )
    require_malware_scan: bool = False

    llm_provider: ProviderType = ProviderType.LOCAL
    embedding_provider: ProviderType = ProviderType.LOCAL
    local_llm_backend: LocalLLMBackend = LocalLLMBackend.EXTRACTIVE
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.2:3b"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    azure_openai_api_key: SecretStr | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    llm_request_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    llm_max_retries: int = Field(default=2, ge=0, le=10)
    llm_max_output_tokens: int = Field(default=1200, ge=64, le=32768)

    embedding_dimension: int = Field(default=384, ge=64, le=8192)
    semantic_embeddings_enabled: bool = False
    semantic_embedding_provider: LocalInferenceProvider = LocalInferenceProvider.LOCAL
    semantic_embedding_model: str = ""
    semantic_embedding_dimension: int = Field(default=384, ge=64, le=8192)
    semantic_embedding_batch_size: int = Field(default=32, ge=1, le=128)
    semantic_embedding_max_length: int = Field(default=512, ge=32, le=2048)
    semantic_embedding_device: str = "cpu"
    semantic_embedding_normalize: bool = True
    semantic_embedding_fallback_enabled: bool = True
    semantic_embedding_max_retries: int = Field(default=2, ge=0, le=5)
    semantic_embedding_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    hybrid_lexical_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    hybrid_semantic_weight: float = Field(default=0.55, ge=0.0, le=1.0)
    reranker_enabled: bool = False
    reranker_provider: LocalInferenceProvider = LocalInferenceProvider.LOCAL
    reranker_model: str = ""
    reranker_top_n: int = Field(default=20, ge=1, le=100)
    reranker_return_k: int = Field(default=8, ge=1, le=50)
    reranker_max_length: int = Field(default=512, ge=32, le=2048)
    reranker_batch_size: int = Field(default=16, ge=1, le=64)
    reranker_device: str = "cpu"
    reranker_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    reranker_fallback_enabled: bool = True
    reranker_blend_weight: float = Field(default=0.25, ge=0.0, le=0.5)
    reranker_min_margin: float = Field(default=0.08, ge=0.0, le=1.0)
    chunk_size: int = Field(default=900, ge=100, le=5000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    retrieval_top_k: int = Field(default=20, ge=1, le=100)
    rerank_top_k: int = Field(default=8, ge=1, le=50)
    evidence_min_score: float = Field(default=0.32, ge=0.0, le=1.0)

    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=60, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    max_request_body_bytes: int = Field(default=30 * 1024 * 1024, ge=1024, le=300 * 1024 * 1024)
    ingestion_stage_delay_seconds: float = Field(default=0.0, ge=0.0, le=10.0)
    log_level: str = "INFO"
    log_json: bool = True
    otel_enabled: bool = False
    otel_service_name: str = "ekip-backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    metrics_enabled: bool = True
    agentic_rag_enabled: bool = False
    agent_max_steps: int = Field(default=6, ge=1, le=25)
    agent_max_tool_calls: int = Field(default=12, ge=0, le=50)
    agent_timeout_seconds: float = Field(default=90.0, gt=0, le=600)
    agent_max_retrieval_retries: int = Field(default=2, ge=0, le=10)
    agent_planner_provider: AgentPlannerProvider = AgentPlannerProvider.DETERMINISTIC
    agent_web_search_enabled: bool = False
    web_search_provider: WebSearchProvider = WebSearchProvider.DISABLED
    web_search_max_results: int = Field(default=5, ge=1, le=20)
    web_search_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    web_search_max_response_bytes: int = Field(default=1_000_000, ge=1024, le=5_000_000)
    agent_external_apis_enabled: bool = False
    searxng_url: str = "http://searxng:8080"
    evidence_max_items: int = Field(default=12, ge=1, le=50)
    evidence_max_internal_items: int = Field(default=8, ge=0, le=50)
    evidence_max_external_items: int = Field(default=6, ge=0, le=50)
    evidence_context_max_chars: int = Field(default=12_000, ge=500, le=100_000)
    evidence_rrf_k: int = Field(default=60, ge=1, le=1000)
    evidence_internal_priority_weight: float = Field(default=1.0, ge=0.0, le=5.0)
    evidence_external_trust_weight: float = Field(default=0.8, ge=0.0, le=5.0)
    evidence_min_support_score: float = Field(default=0.65, ge=0.0, le=1.0)
    evidence_trust_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "internal_document": 1.0,
            "web_search": 0.55,
            "searxng": 0.6,
            "wikipedia": 0.8,
            "arxiv": 0.85,
            "approved_api": 0.75,
            "deterministic": 0.6,
        }
    )
    agent_research_enabled: bool = False
    agent_research_max_steps: int = Field(default=12, ge=1, le=50)
    agent_research_max_tool_calls: int = Field(default=20, ge=1, le=100)
    agent_research_max_sources: int = Field(default=20, ge=1, le=100)
    agent_research_timeout_seconds: float = Field(default=300.0, gt=0, le=1800)
    agent_research_max_report_words: int = Field(default=5000, ge=100, le=50_000)
    agent_research_max_concurrent_per_user: int = Field(default=3, ge=1, le=100)
    agent_research_max_concurrent_per_workspace: int = Field(default=10, ge=1, le=500)
    agent_research_max_queued_jobs: int = Field(default=100, ge=1, le=10_000)
    agent_research_stage_delay_seconds: float = Field(default=0.0, ge=0.0, le=10.0)
    agent_research_external_sources_default: bool = False
    agent_research_allowed_formats: list[str] = Field(
        default_factory=lambda: ["markdown", "pdf", "docx"]
    )
    agent_research_signed_url_ttl_seconds: int = Field(default=600, ge=60, le=3600)

    @field_validator(
        "app_env",
        "llm_provider",
        "embedding_provider",
        "object_storage_provider",
        "job_execution_mode",
        "local_llm_backend",
        "agent_planner_provider",
        "web_search_provider",
        "semantic_embedding_provider",
        "reranker_provider",
        mode="before",
    )
    @classmethod
    def normalize_enums(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator(
        "cors_origins",
        "trusted_hosts",
        "allowed_file_extensions",
        "allowed_mime_types",
        "agent_research_allowed_formats",
        "evidence_trust_weights",
        mode="before",
    )
    @classmethod
    def parse_jsonish(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            return {} if value.startswith("{") else []
        if value.startswith("{"):
            result = json.loads(value)
            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            return result
        if value.startswith("["):
            result = json.loads(value)
            if not isinstance(result, list):
                raise ValueError("Expected a JSON list")
            return result
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("allowed_file_extensions")
    @classmethod
    def normalize_extensions(cls, values: list[str]) -> list[str]:
        return sorted({v.lower() if v.startswith(".") else f".{v.lower()}" for v in values})

    @field_validator("evidence_trust_weights")
    @classmethod
    def validate_trust_weights(cls, values: dict[str, Any]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for key, value in values.items():
            weight = float(value)
            if weight < 0.0 or weight > 1.0:
                raise ValueError("Evidence trust weights must be between 0 and 1")
            normalized[str(key)] = weight
        return normalized

    @field_validator("agent_research_allowed_formats")
    @classmethod
    def validate_research_formats(cls, values: list[str]) -> list[str]:
        allowed = {"markdown", "pdf", "docx"}
        normalized = sorted({value.strip().lower() for value in values if value.strip()})
        if not normalized or any(value not in allowed for value in normalized):
            raise ValueError("Research formats must be markdown, pdf, or docx")
        return normalized

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if normalized in {"release", "prod", "production"}:
            return False
        if normalized in {"debug", "dev", "development"}:
            return True
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        return "/" + value.strip().strip("/")

    @model_validator(mode="after")
    def validate_security(self) -> Self:
        if "*" in self.cors_origins and self.cors_allow_credentials:
            raise ValueError("Wildcard CORS cannot be combined with credentials")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.rerank_top_k > self.retrieval_top_k:
            raise ValueError("RERANK_TOP_K cannot exceed RETRIEVAL_TOP_K")
        if self.reranker_return_k > self.reranker_top_n:
            raise ValueError("RERANKER_RETURN_K cannot exceed RERANKER_TOP_N")
        if abs(self.hybrid_lexical_weight + self.hybrid_semantic_weight - 1.0) > 1e-6:
            raise ValueError("Hybrid lexical and semantic weights must sum to 1")
        if self.semantic_embedding_device != "cpu" or self.reranker_device != "cpu":
            raise ValueError("Phase 2 local inference is restricted to CPU")
        if self.llm_provider is ProviderType.OPENAI and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        if self.is_production:
            secret = self.secret_key.get_secret_value()
            if len(secret) < 32 or secret.startswith("development-") or "replace" in secret.lower():
                raise ValueError("Production SECRET_KEY must be a unique 32+ character value")
            if self.debug or self.database_echo:
                raise ValueError("Debug and SQL echo must be disabled in production")
            if any(origin.startswith("http://") for origin in self.cors_origins):
                raise ValueError("Production CORS origins must use HTTPS")
        return self

    @property
    def is_testing(self) -> bool:
        return self.app_env is AppEnvironment.TESTING

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnvironment.PRODUCTION

    @property
    def docs_url(self) -> str | None:
        return None if self.is_production else "/docs"

    @property
    def openapi_url(self) -> str | None:
        return None if self.is_production else "/openapi.json"

    @property
    def redoc_url(self) -> str | None:
        return None if self.is_production else "/redoc"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
