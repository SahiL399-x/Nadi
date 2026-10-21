from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


@lru_cache(maxsize=1)
def _client():
    # Built once and reused; boto3 client creation parses the service model and is
    # expensive to repeat on every presign request.
    return boto3.client(
        "s3", endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_key, aws_secret_access_key=settings.s3_secret,
        config=Config(signature_version="s3v4"), region_name="us-east-1",
    )


def presign_put(object_key: str) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=300,
    )


def ensure_bucket() -> None:
    """Create the reports bucket if it does not exist, so a fresh stack accepts
    report uploads with no manual MinIO setup. Idempotent; called on API startup."""
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)
