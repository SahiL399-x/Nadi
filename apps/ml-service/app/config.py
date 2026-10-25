from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MinIO / S3 (mirrors apps/api defaults so the same creds work in dev).
    s3_endpoint: str = "http://localhost:9000"
    s3_key: str = "nadi"
    s3_secret: str = "nadi12345"
    s3_bucket: str = "nadi-reports"

    # Real OCR is off until the benchmark passes; off == today's stub behavior.
    ml_ocr_enabled: bool = False


settings = Settings()
