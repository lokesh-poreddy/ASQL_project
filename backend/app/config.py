"""Typed configuration.

Every experimental/tunable value is a field here, sourced from environment
variables / .env via pydantic-settings — never a literal buried in
application code. This is what makes the system reproducible: the
configuration fully determines the experiment.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class EmbeddingProviderKind(str, Enum):
    HASHING = "hashing"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = Field(default=AppEnv.DEVELOPMENT, alias="APP_ENV")

    # ── Oracle ────────────────────────────────────────────────────────────────
    oracle_user: str = Field(default="nexus_sql_app", alias="ORACLE_USER")
    oracle_password: str = Field(default="", alias="ORACLE_PASSWORD")
    oracle_dsn: str = Field(default="localhost:1521/FREEPDB1", alias="ORACLE_DSN")
    oracle_pool_min: int = Field(default=2, alias="ORACLE_POOL_MIN")
    oracle_pool_max: int = Field(default=10, alias="ORACLE_POOL_MAX")
    oracle_pool_increment: int = Field(default=2, alias="ORACLE_POOL_INCREMENT")
    oracle_wallet_location: str = Field(default="", alias="ORACLE_WALLET_LOCATION")

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_provider: EmbeddingProviderKind = Field(
        default=EmbeddingProviderKind.HASHING, alias="EMBEDDING_PROVIDER"
    )
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME"
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")

    # ── Retrieval / ranking defaults ──────────────────────────────────────────
    default_top_k: int = Field(default=10, alias="DEFAULT_TOP_K")
    # alpha ∈ [0,1]: semantic weight; (1-alpha) is SQL/structured weight
    hybrid_alpha: float = Field(default=0.5, alias="HYBRID_ALPHA")
    candidate_multiplier: int = Field(default=4, alias="CANDIDATE_MULTIPLIER")

    # ── Resource optimizer defaults ───────────────────────────────────────────
    storage_budget_mb: float = Field(default=500.0, alias="STORAGE_BUDGET_MB")
    latency_budget_ms: float = Field(default=300.0, alias="LATENCY_BUDGET_MS")
    accuracy_target_recall_at_10: float = Field(
        default=0.90, alias="ACCURACY_TARGET_RECALL_AT_10"
    )

    # ── Error recovery ────────────────────────────────────────────────────────
    max_recovery_attempts: int = Field(default=3, alias="MAX_RECOVERY_ATTEMPTS")

    # ── API server ────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: str = Field(
        default="http://localhost:5500,http://127.0.0.1:5500",
        alias="CORS_ORIGINS",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_test_mode(self) -> bool:
        return self.app_env == AppEnv.TEST

    @property
    def use_oracle(self) -> bool:
        """True only when Oracle credentials are present and not in test mode."""
        return (
            not self.is_test_mode
            and bool(self.oracle_password)
            and bool(self.oracle_dsn)
        )

    @field_validator("hybrid_alpha")
    @classmethod
    def validate_alpha(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("hybrid_alpha must be in [0, 1]")
        return v

    @field_validator("accuracy_target_recall_at_10")
    @classmethod
    def validate_accuracy(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError("accuracy_target_recall_at_10 must be in (0, 1]")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton. Cached so every module sees the same
    instance and .env is parsed exactly once."""
    return Settings()
