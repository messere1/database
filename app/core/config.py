from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Crime Analytics API"
    app_env: str = "dev"
    app_debug: bool = True
    app_cors_origins: str = "*"

    og_host: str = "1.95.135.195"
    og_port: int = 26000
    og_database: str = "testdb"
    og_user: str = "testuser"
    og_password: str = "DBlab@123"
    og_schema: str = "testuser"
    og_sslmode: str = "prefer"
    og_connect_timeout: int = 15
    og_analysis_table: str = "crimes_clean"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def opengauss_iri(self) -> str:
        return f"opengauss://{self.og_user}@{self.og_host}:{self.og_port}/{self.og_database}"

    @property
    def cors_origins(self) -> list[str]:
        if self.app_cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
