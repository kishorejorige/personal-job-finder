from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "Personal Job Finder"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8010
    DATABASE_URL: str = "sqlite:///./jobs.db"
    CORS_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"
    LOG_LEVEL: str = "INFO"
    MAX_RESUME_SIZE_MB: int = 2
    PROVIDER_REFRESH_COOLDOWN_MINUTES: int = 15
    REQUEST_TIMEOUT_SECONDS: int = 10
    MAX_EXPORT_ROWS: int = 1000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
