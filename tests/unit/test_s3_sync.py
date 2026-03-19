from unittest.mock import MagicMock, patch

import pytest
from minio.error import S3Error

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


def test_upload(config, mock_client, tmp_path):
    from scholartools.adapters import s3_sync

    local_file = tmp_path / "test.json"
    local_file.write_text("{}")

    s3_sync.upload(config, local_file, "changes/peer/ts.json")
    mock_client.fput_object.assert_called_once_with(
        "test-bucket", "changes/peer/ts.json", str(local_file)
    )


def test_download(config, mock_client, tmp_path):
    from scholartools.adapters import s3_sync

    local_path = tmp_path / "out.json"
    s3_sync.download(config, "changes/peer/ts.json", local_path)
    mock_client.fget_object.assert_called_once_with(
        "test-bucket", "changes/peer/ts.json", str(local_path)
    )


def test_list_keys(config, mock_client):
    from scholartools.adapters import s3_sync

    obj1 = MagicMock()
    obj1.object_name = "changes/peer/t1.json"
    obj2 = MagicMock()
    obj2.object_name = "changes/peer/t2.json"
    mock_client.list_objects.return_value = [obj1, obj2]

    result = s3_sync.list_keys(config, "changes/")
    assert result == ["changes/peer/t1.json", "changes/peer/t2.json"]


def test_list_keys_empty(config, mock_client):
    from scholartools.adapters import s3_sync

    mock_client.list_objects.return_value = []

    result = s3_sync.list_keys(config, "changes/")
    assert result == []


def test_exists_true(config, mock_client):
    from scholartools.adapters import s3_sync

    result = s3_sync.exists(config, "changes/peer/ts.json")
    assert result is True


def test_exists_false(config, mock_client):
    from scholartools.adapters import s3_sync

    mock_client.stat_object.side_effect = S3Error(
        "NoSuchKey",
        "The specified key does not exist.",
        "/bucket/key",
        "req-id",
        "host-id",
        None,
    )
    result = s3_sync.exists(config, "missing.json")
    assert result is False
