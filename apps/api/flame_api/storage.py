import boto3
from botocore.config import Config

from flame_api.config import get_settings


def client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        config=Config(connect_timeout=2, read_timeout=10, retries={"total_max_attempts": 2}),
    )


def put_bytes(key: str, content: bytes, media_type: str) -> None:
    settings = get_settings()
    client().put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=media_type)


def put_file(key: str, path: str, media_type: str) -> None:
    settings = get_settings()
    client().upload_file(path, settings.s3_bucket, key, ExtraArgs={"ContentType": media_type})


def get_bytes(key: str) -> bytes:
    settings = get_settings()
    return client().get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()


def delete(key: str) -> None:
    settings = get_settings()
    client().delete_object(Bucket=settings.s3_bucket, Key=key)