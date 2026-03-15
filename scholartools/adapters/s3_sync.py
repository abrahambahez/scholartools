from pathlib import Path

from scholartools.models import SyncConfig


def _client(config: SyncConfig):
    try:
        import boto3
    except ImportError:
        raise ImportError(
            "boto3 is required for S3 sync. Install it with: pip install boto3"
        )
    kwargs = dict(
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
    )
    if config.endpoint:
        kwargs["endpoint_url"] = config.endpoint
    return boto3.client("s3", **kwargs)


def upload(config: SyncConfig, local_path: Path, remote_key: str) -> None:
    _client(config).upload_file(str(local_path), config.bucket, remote_key)


def download(config: SyncConfig, remote_key: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    _client(config).download_file(config.bucket, remote_key, str(local_path))


def list_keys(config: SyncConfig, prefix: str) -> list[str]:
    paginator = _client(config).get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=config.bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def exists(config: SyncConfig, remote_key: str) -> bool:
    try:
        _client(config).head_object(Bucket=config.bucket, Key=remote_key)
        return True
    except Exception:
        return False


def upload_bytes(config: SyncConfig, data: bytes, remote_key: str) -> None:
    import io

    _client(config).put_object(
        Bucket=config.bucket, Key=remote_key, Body=io.BytesIO(data)
    )
