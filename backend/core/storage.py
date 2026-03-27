import io
import logging

from minio import Minio
from minio.error import S3Error

from core.config import settings

logger = logging.getLogger(__name__)

BUCKETS = ["structures", "molecules", "results"]


def _get_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


def ensure_buckets() -> None:
    """Create required buckets if they don't exist."""
    client = _get_client()
    for bucket in BUCKETS:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f"Created MinIO bucket: {bucket}")
        except S3Error as e:
            logger.warning(f"Could not check/create bucket '{bucket}': {e}")


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to MinIO and return the object path."""
    client = _get_client()
    client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return f"{bucket}/{key}"


def download_file(bucket: str, key: str) -> bytes:
    """Download an object from MinIO and return its bytes."""
    client = _get_client()
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def file_exists(bucket: str, key: str) -> bool:
    """Check if an object exists in MinIO."""
    client = _get_client()
    try:
        client.stat_object(bucket, key)
        return True
    except S3Error:
        return False
