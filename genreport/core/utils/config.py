"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="GenReport")
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(...)
    api_version: str = Field(default="v1")

    # Database
    database_url: PostgresDsn = Field(...)
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=10)

    # Redis
    redis_url: RedisDsn = Field(...)
    redis_password: str = Field(default="")

    # Celery
    celery_broker_url: RedisDsn = Field(...)
    celery_result_backend: RedisDsn = Field(...)

    # JWT
    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)

    # Encryption
    encryption_key: str = Field(...)

    # AWS KMS
    aws_region: str = Field(default="ap-east-1")
    aws_kms_key_id: str = Field(default="")

    # LLM Provider Selection
    default_llm_provider: str = Field(default="gemini")

    # Google Gemini (Default Provider)
    google_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_max_tokens: int = Field(default=8192)
    gemini_temperature: float = Field(default=0.1)

    # OpenAI (Optional Alternative)
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_max_tokens: int = Field(default=4096)
    openai_temperature: float = Field(default=0.1)

    # Langfuse
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_auth_per_minute: int = Field(default=5)

    # CORS
    cors_origins: str = Field(default="http://localhost:3000")
    cors_allow_credentials: bool = Field(default=True)

    # File Upload
    max_file_size_mb: int = Field(default=50)
    upload_dir: str = Field(default="./uploads")
    encrypted_upload_dir: str = Field(default="./encrypted")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # Security
    allowed_hosts: str = Field(default="localhost,127.0.0.1")
    trusted_hosts: str = Field(default="localhost,127.0.0.1")

    # Multi-Region
    data_residency_region: str = Field(default="HK")
    supported_regions: str = Field(default="HK,SG,AU")

    # Feature Flags
    enable_audit_logging: bool = Field(default=True)
    enable_pii_detection: bool = Field(default=True)
    enable_context_validation: bool = Field(default=True)

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get allowed hosts as list."""
        if isinstance(self.allowed_hosts, str):
            return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return self.allowed_hosts

    @property
    def trusted_hosts_list(self) -> List[str]:
        """Get trusted hosts as list."""
        if isinstance(self.trusted_hosts, str):
            return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]
        return self.trusted_hosts

    @property
    def supported_regions_list(self) -> List[str]:
        """Get supported regions as list."""
        if isinstance(self.supported_regions, str):
            return [region.strip() for region in self.supported_regions.split(",") if region.strip()]
        return self.supported_regions

    @property
    def database_url_str(self) -> str:
        """Get database URL as string."""
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        """Get Redis URL as string."""
        return str(self.redis_url)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.app_env == "test"

    @property
    def llm_api_key(self) -> str:
        """Get the API key for the default LLM provider."""
        if self.default_llm_provider == "gemini":
            return self.google_api_key
        elif self.default_llm_provider == "openai":
            return self.openai_api_key
        return ""

    @property
    def llm_model(self) -> str:
        """Get the model name for the default LLM provider."""
        if self.default_llm_provider == "gemini":
            return self.gemini_model
        elif self.default_llm_provider == "openai":
            return self.openai_model
        return ""

    @property
    def llm_max_tokens(self) -> int:
        """Get the max tokens for the default LLM provider."""
        if self.default_llm_provider == "gemini":
            return self.gemini_max_tokens
        elif self.default_llm_provider == "openai":
            return self.openai_max_tokens
        return 4096

    @property
    def llm_temperature(self) -> float:
        """Get the temperature for the default LLM provider."""
        if self.default_llm_provider == "gemini":
            return self.gemini_temperature
        elif self.default_llm_provider == "openai":
            return self.openai_temperature
        return 0.1


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
