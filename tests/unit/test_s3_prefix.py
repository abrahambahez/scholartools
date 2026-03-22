from unittest.mock import MagicMock, patch

import pytest

from scholartools.adapters.s3_sync import _split
from scholartools.models import SyncConfig


def cfg(bucket: str) -> SyncConfig:
    return SyncConfig(
        endpoint="http://localhost:9000",
        bucket=bucket,
        access_key="a",
        secret_key="s",
    )


# _split


def test_split_no_slash():
    assert _split(cfg("mybucket")) == ("mybucket", "")


def test_split_single_segment():
    assert _split(cfg("mybucket/proj")) == ("mybucket", "proj/")


def test_split_multi_segment():
    assert _split(cfg("mybucket/a/b")) == ("mybucket", "a/b/")


def test_split_trailing_slash():
    assert _split(cfg("mybucket/")) == ("mybucket", "")


# operations with prefix


@pytest.fixture
def prefixed_config():
    return cfg("mybucket/proj")


@pytest.fixture
def mock_client():
    instance = MagicMock()
    with patch("scholartools.adapters.s3_sync.Minio", return_value=instance):
        yield instance


def test_upload_prepends_prefix(prefixed_config, mock_client, tmp_path):
    from scholartools.adapters import s3_sync

    local_file = tmp_path / "f.json"
    local_file.write_text("{}")
    s3_sync.upload(prefixed_config, local_file, "changes/peer/ts.json")
    mock_client.fput_object.assert_called_once_with(
        "mybucket", "proj/changes/peer/ts.json", str(local_file)
    )


def test_download_prepends_prefix(prefixed_config, mock_client, tmp_path):
    from scholartools.adapters import s3_sync

    local_path = tmp_path / "out.json"
    s3_sync.download(prefixed_config, "blobs/sha256", local_path)
    mock_client.fget_object.assert_called_once_with(
        "mybucket", "proj/blobs/sha256", str(local_path)
    )


def test_list_keys_prepends_and_strips(prefixed_config, mock_client):
    from scholartools.adapters import s3_sync

    obj1 = MagicMock()
    obj1.object_name = "proj/changes/peer/t1.json"
    obj2 = MagicMock()
    obj2.object_name = "proj/changes/peer/t2.json"
    mock_client.list_objects.return_value = [obj1, obj2]

    result = s3_sync.list_keys(prefixed_config, "changes/")
    mock_client.list_objects.assert_called_once_with(
        "mybucket", prefix="proj/changes/", recursive=True
    )
    assert result == ["changes/peer/t1.json", "changes/peer/t2.json"]


def test_exists_prepends_prefix(prefixed_config, mock_client):
    from scholartools.adapters import s3_sync

    assert s3_sync.exists(prefixed_config, "snapshots/ts.json") is True
    mock_client.stat_object.assert_called_once_with(
        "mybucket", "proj/snapshots/ts.json"
    )


def test_upload_bytes_prepends_prefix(prefixed_config, mock_client):
    from scholartools.adapters import s3_sync

    data = b"bytes"
    s3_sync.upload_bytes(prefixed_config, data, "blobs/sha256")
    args = mock_client.put_object.call_args.args
    assert args[0] == "mybucket"
    assert args[1] == "proj/blobs/sha256"
