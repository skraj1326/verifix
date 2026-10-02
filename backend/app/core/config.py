"""Core configuration for AstrixCore Verification AI platform."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AstrixCore Verification AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default="change-me-in-production")
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://astrixcore:astrixcore@localhost:5432/astrixcore"
    )
    DATABASE_SYNC_URL: str = Field(
        default="postgresql://astrixcore:astrixcore@localhost:5432/astrixcore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_database_url(cls, value):
        """Convert Render's PostgreSQL URL to asyncpg format."""
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1
            )
        return value

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # File Storage
    STORAGE_ROOT: Path = Field(default=Path("./storage"))
    RTL_STORAGE: Path = Field(default=Path("./storage/rtl"))
    TEST_STORAGE: Path = Field(default=Path("./storage/tests"))
    LOG_STORAGE: Path = Field(default=Path("./storage/logs"))
    COVERAGE_STORAGE: Path = Field(default=Path("./storage/coverage"))

    # LLM Configuration
    LLM_PROVIDER: str = Field(default="openai")
    LLM_API_KEY: Optional[str] = Field(default=None)
    LLM_MODEL: str = Field(default="gpt-4o")
    LLM_BASE_URL: Optional[str] = Field(default=None)
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_MAX_TOKENS: int = Field(default=4096)

    # Simulation
    VERILATOR_PATH: str = Field(default="verilator")
    ICARUS_PATH: str = Field(default="iverilog")
    SIMULATION_TIMEOUT: int = Field(default=300)
    MAX_CONCURRENT_SIMS: int = Field(default=4)

    # AI Agent
    AI_ENABLED: bool = Field(default=True)
    AI_CONFIDENCE_THRESHOLD: float = Field(default=0.6)
    AI_MAX_RETRIES: int = Field(default=3)

    # Security
    ENCRYPTION_KEY: Optional[str] = Field(default=None)
    AUDIT_LOG_ENABLED: bool = Field(default=True)
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"]
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

    def ensure_storage_dirs(self) -> None:
        """Create storage directories if they don't exist."""
        for path in [
            self.STORAGE_ROOT,
            self.RTL_STORAGE,
            self.TEST_STORAGE,
            self.LOG_STORAGE,
            self.COVERAGE_STORAGE,
        ]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_storage_dirs()
