"""Abstração de storage (object storage, ex.: MinIO/S3)."""

import os
from typing import Protocol

BUCKET = "einstein"


class Storage(Protocol):
    def upload(self, bucket: str, path: str, content: bytes) -> str: ...
    def download(self, bucket: str, path: str) -> bytes: ...
    def delete(self, bucket: str, path: str) -> None: ...
    def ensure_bucket(self, name: str | None = None) -> None: ...


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

    def ensure_bucket(self, name: str | None = None) -> None:
        """Garante que o bucket existe — cria se não existir (idempotente).

        Tolerante ao boot: se o MinIO estiver indisponível ou outro processo
        criar o bucket na mesma corrida (409/BucketAlreadyOwnedByYou), registra
        e segue em vez de impedir o boot da app.
        """
        from botocore.exceptions import ClientError

        from einstein_test.logging_setup import get_logger

        logger = get_logger("storage.minio")
        bucket = name or self.bucket
        try:
            self._s3.head_bucket(Bucket=bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket"):
                logger.info("bucket ausente — criando", extra={
                    "event": "bucket_ensure", "bucket": bucket,
                })
                try:
                    self._s3.create_bucket(Bucket=bucket)
                except ClientError as create_exc:
                    create_code = create_exc.response.get("Error", {}).get("Code", "")
                    if create_code in (
                        "BucketAlreadyOwnedByYou",
                        "BucketAlreadyExists",
                        "409",
                    ):
                        # corrida: outro worker/replica criou primeiro — ok
                        return
                    raise
                except Exception:  # noqa: BLE001 - MinIO fora do ar
                    logger.error("bucket indisponível ao criar", extra={
                        "event": "bucket_ensure_unavailable", "bucket": bucket,
                    })
                    return
                return
            raise
        except Exception as exc:  # noqa: BLE001 - MinIO fora do ar no boot
            logger.error("bucket indisponível no startup", extra={
                "event": "bucket_ensure_unavailable", "bucket": bucket,
                "error": type(exc).__name__,
            })

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

    def download(self, bucket: str, path: str) -> bytes:
        response = self._s3.get_object(Bucket=bucket, Key=path)
        return response["Body"].read()

    def delete(self, bucket: str, path: str) -> None:
        self._s3.delete_object(Bucket=bucket, Key=path)