"""
Thin wrapper around boto3 for S3 operations.
Provides presigned URL generation and object management.
"""

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from app.core.config import settings


def get_s3_client():
    """Return a configured boto3 S3 client."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
        config=BotoConfig(signature_version="s3v4"),
    )


def generate_presigned_upload_url(
    key: str,
    content_type: str,
    expires_in: int = 900,  # 15 minutes
) -> str:
    """Generate a presigned PUT URL for direct client-to-S3 uploads."""
    client = get_s3_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )


def generate_presigned_download_url(
    key: str,
    expires_in: int = 3600,  # 1 hour
) -> str:
    """Generate a presigned GET URL for secure file downloads."""
    client = get_s3_client()
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": key,
        },
        ExpiresIn=expires_in,
    )


def head_s3_object(key: str) -> dict | None:
    """
    Check if an object exists in S3 and return its metadata.
    Returns None if the object does not exist.
    """
    client = get_s3_client()
    try:
        return client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    except ClientError:
        return None


def delete_s3_object(key: str) -> None:
    """Delete an object from S3."""
    client = get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
