import sys
from unittest.mock import MagicMock

import pytest

from scholartools.models import SyncConfig


@pytest.fixture
def config():
    return SyncConfig(
        endpoint="http://localhost:9000",
        bucket="test-bucket",
        access_key="access",
        secret_key="secret",
    )


@pytest.fixture(autouse=True)
def mock_boto3(monkeypatch):
    boto3_mock = MagicMock()
    botocore_mock = MagicMock()
    botocore_config_mock = MagicMock()
    monkeypatch.setitem(sys.modules, "boto3", boto3_mock)
    monkeypatch.setitem(sys.modules, "botocore", botocore_mock)
    monkeypatch.setitem(sys.modules, "botocore.config", botocore_config_mock)
    return boto3_mock


def test_upload_bytes_calls_put_object(config, mock_boto3):
    from scholartools.adapters import s3_sync

    data = b"meta json content"
    s3_sync.upload_bytes(config, data, "blobs/abc123.meta")
    mock_boto3.client.return_value.put_object.assert_called_once()
    call_kwargs = mock_boto3.client.return_value.put_object.call_args
    assert call_kwargs.kwargs["Bucket"] == "test-bucket"
    assert call_kwargs.kwargs["Key"] == "blobs/abc123.meta"
    body = call_kwargs.kwargs["Body"]
    assert body.read() == data


def test_upload_bytes_empty(config, mock_boto3):
    from scholartools.adapters import s3_sync

    s3_sync.upload_bytes(config, b"", "blobs/empty.meta")
    mock_boto3.client.return_value.put_object.assert_called_once()


def test_upload_bytes_uses_correct_bucket(config, mock_boto3):
    from scholartools.adapters import s3_sync

    s3_sync.upload_bytes(config, b"data", "blobs/key.meta")
    call_kwargs = mock_boto3.client.return_value.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "test-bucket"
