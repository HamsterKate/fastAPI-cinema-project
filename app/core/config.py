from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_env: str
    debug: bool

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    smtp_host: str
    smtp_port: int
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str

    minio_endpoint: str
    minio_public_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str
    minio_presigned_url_expire_seconds: int

    api_prefix: str = "/api/v2"

    activation_url: str
    activation_token_expire_minutes: int = 15

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    stripe_secret_key: str
    stripe_webhook_secret: str = ""
    stripe_currency: str = "usd"
    stripe_success_url: str
    stripe_cancel_url: str

    password_reset_url: str
    password_reset_token_expire_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
