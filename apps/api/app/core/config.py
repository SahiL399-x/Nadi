from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nadi:nadi@localhost:5433/nadi"
    ml_service_url: str = "http://localhost:8001"
    jwt_secret: str = "dev-secret-change-me"
    jwt_alg: str = "HS256"
    access_ttl_min: int = 30
    refresh_ttl_days: int = 30
    s3_endpoint: str = "http://localhost:9000"
    s3_key: str = "nadi"
    s3_secret: str = "nadi12345"
    s3_bucket: str = "nadi-reports"
    otp_stub_code: str = "123456"
    # LiveKit (in-app video). Key/secret match the self-hosted dev server in
    # infra/docker-compose.yml. livekit_url is handed to the client, so for the
    # LAN demo override it with the laptop's LAN IP (ws://<ip>:7880).
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "nadidevsecret0123456789abcdef0123456789"


settings = Settings()
