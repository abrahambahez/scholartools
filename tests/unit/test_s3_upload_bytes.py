from unittest.mock import patch

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


@pytest.fixture
def mock_client():
    with patch("scholartools.adapters.s3_sync._client") as p:
        yield p.return_value


def test_upload_bytes_calls_put_object(config, mock_client):
    from scholartools.adapters import s3_sync

    data = b"meta json content"
    s3_sync.upload_bytes(config, data, "blobs/abc123.meta")
    mock_client.put_object.assert_called_once()
    args = mock_client.put_object.call_args.args
    assert args[0] == "test-bucket"
    assert args[1] == "blobs/abc123.meta"
    assert args[2].read() == data
    assert args[3] == len(data)


def test_upload_bytes_empty(config, mock_client):
    from scholartools.adapters import s3_sync

    s3_sync.upload_bytes(config, b"", "blobs/empty.meta")
    mock_client.put_object.assert_called_once()


def test_upload_bytes_uses_correct_bucket(config, mock_client):
    from scholartools.adapters import s3_sync

    s3_sync.upload_bytes(config, b"data", "blobs/key.meta")
    args = mock_client.put_object.call_args.args
    assert args[0] == "test-bucket"
