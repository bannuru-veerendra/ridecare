import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        extra="ignore",
    )

    APP_ENV: str
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_VERIFY_TOKEN_EXPIRE_HOURS: int = 24
    FRONTEND_URL: str = "http://localhost:5173"
    EMAIL_FROM: str = "RideCare <noreply@example.com>"
    # SMTP. Example Gmail: smtp.gmail.com:587 + app password.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: bool = True
    DATABASE_URL: str
    REDIS_URL: str
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_STORAGE_BUCKET: str
    ALLOWED_ORIGINS: str = "http://localhost:5173"


settings = Settings()
