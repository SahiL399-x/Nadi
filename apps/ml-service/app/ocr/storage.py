from functools import lru_cache

import boto3
from botocore.client import Config

from app.config import settings


class StorageError(Exception):
    """Raised when an object cannot be fetched."""


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3", endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_key, aws_secret_access_key=settings.s3_secret,
        config=Config(signature_version="s3v4"), region_name="us-east-1",
    )


def fetch_object(object_key: str) -> bytes:
    try:
        obj = _client().get_object(Bucket=settings.s3_bucket, Key=object_key)
        return obj["Body"].read()
    except Exception as exc:  # noqa: BLE001 — surface a typed error, never leak key/content
        raise StorageError(f"could not fetch object (len={len(object_key)})") from exc
