import io
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from scholartools.models import SyncConfig


def _client(config: SyncConfig) -> Minio:
    if config.endpoint:
        parsed = urlparse(config.endpoint)
        host = parsed.netloc or parsed.path
        secure = parsed.scheme == "https"
    else:
        host = "s3.amazonaws.com"
        secure = True
    return Minio(
        host, access_key=config.access_key, secret_key=config.secret_key, secure=secure
    )


def _split(config: SyncConfig) -> tuple[str, str]:
    if "/" not in config.bucket:
        return config.bucket, ""
    bucket, subdir = config.bucket.split("/", 1)
    return bucket, f"{subdir}/" if subdir else ""


def upload(config: SyncConfig, local_path: Path, remote_key: str) -> None:
    bucket, prefix = _split(config)
    _client(config).fput_object(bucket, prefix + remote_key, str(local_path))


def download(config: SyncConfig, remote_key: str, local_path: Path) -> None:
    bucket, prefix = _split(config)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    _client(config).fget_object(bucket, prefix + remote_key, str(local_path))


def list_keys(config: SyncConfig, prefix: str) -> list[str]:
    bucket, cfg_prefix = _split(config)
    strip = len(cfg_prefix)
    return [
        obj.object_name[strip:]
        for obj in _client(config).list_objects(
            bucket, prefix=cfg_prefix + prefix, recursive=True
        )
    ]


def exists(config: SyncConfig, remote_key: str) -> bool:
    bucket, prefix = _split(config)
    try:
        _client(config).stat_object(bucket, prefix + remote_key)
        return True
    except S3Error:
        return False


def upload_bytes(config: SyncConfig, data: bytes, remote_key: str) -> None:
    bucket, prefix = _split(config)
    _client(config).put_object(bucket, prefix + remote_key, io.BytesIO(data), len(data))
