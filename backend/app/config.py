"""Application configuration, loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SCOPES = (
    "openid"
    " https://www.googleapis.com/auth/userinfo.email"
    " https://www.googleapis.com/auth/userinfo.profile"
    " https://www.googleapis.com/auth/drive.file"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Database ---------------------------------------------------------
    database_url: str = Field(
        default="sqlite+pysqlite:///./meridian.db",
        description="SQLAlchemy URL. Postgres in docker-compose; SQLite for a zero-setup spike.",
    )

    # --- Secrets ----------------------------------------------------------
    app_secret: str = Field(default="dev-insecure-secret-change-me")
    token_encryption_key: str = Field(default="")

    # --- Google OAuth -----------------------------------------------------
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = Field(default="http://localhost:8000/api/auth/google/callback")
    oauth_scopes: str = Field(default=DEFAULT_SCOPES)

    # --- URLs -------------------------------------------------------------
    frontend_url: str = Field(default="http://localhost:5173")
    backend_url: str = Field(default="http://localhost:8000")

    # --- Session ----------------------------------------------------------
    session_cookie_name: str = Field(default="meridian_session")
    session_ttl_minutes: int = Field(default=60 * 12)
    session_cookie_secure: bool = Field(default=False)
    session_cookie_samesite: str = Field(default="lax")

    # --- Local development ------------------------------------------------
    dev_login_enabled: bool = Field(
        default=False,
        description="Enables POST /api/auth/dev-login. Never enable outside local dev.",
    )
    dev_login_email: str = Field(default="demo@meridian.local")

    # --- Behaviour --------------------------------------------------------
    evidence_folder_name: str = Field(default="Meridian Evidence")
    auth_rate_limit_per_minute: int = Field(default=20)
    import_rate_limit_per_minute: int = Field(default=10)

    @field_validator("session_cookie_samesite")
    @classmethod
    def _valid_samesite(cls, v: str) -> str:
        v = v.lower()
        if v not in {"lax", "strict", "none"}:
            raise ValueError("session_cookie_samesite must be lax, strict or none")
        return v

    # --- Derived ----------------------------------------------------------
    @property
    def scopes_list(self) -> list[str]:
        return [s for s in self.oauth_scopes.replace(",", " ").split() if s]

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.frontend_url.rstrip("/")}
        # Vite sometimes serves on 127.0.0.1 rather than localhost.
        origins.add(self.frontend_url.rstrip("/").replace("localhost", "127.0.0.1"))
        return sorted(origins)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
