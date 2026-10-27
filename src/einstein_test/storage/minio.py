"""Abstração de storage (object storage, ex.: MinIO/S3)."""

import os
from typing import Protocol

BUCKET = "einstein"


class Storage(Protocol):
    def upload(self, bucket: str, path: str, content: bytes) -> str: ...
    def delete(self, bucket: str, path: str) -> None: ...


class MinioStorage:
    """Upload via boto3 contra o MinIO local (config do compose F-001)."""

    bucket = BUCKET

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        import boto3

        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint or os.getenv(
                "MINIO_ENDPOINT", "http://localhost:9000"
            ),
            aws_access_key_id=access_key or os.getenv(
                "MINIO_ROOT_USER", "minioadmin"
            ),
            aws_secret_access_key=secret_key or os.getenv(
                "MINIO_ROOT_PASSWORD", "minioadmin"
            ),
            region_name="us-east-1",
        )

    def upload(
        self, bucket: str, path: str, content: bytes, content_type: str | None = None
    ) -> str:
        self._s3.put_object(
            Bucket=bucket,
            Key=path,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )
        return f"s3://{bucket}/{path}"

    def delete(self, bucket: str, path: str) -> None:
        self._s3.delete_object(Bucket=bucket, Key=path)