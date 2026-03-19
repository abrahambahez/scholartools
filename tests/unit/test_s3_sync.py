import sys
from unittest.mock import MagicMock, patch

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


def test_upload(config, mock_boto3, tmp_path):
    from scholartools.adapters import s3_sync

    local_file = tmp_path / "test.json"
    local_file.write_text("{}")

    s3_sync.upload(config, local_file, "changes/peer/ts.json")
    mock_boto3.client.return_value.upload_file.assert_called_once_with(
        str(local_file), "test-bucket", "changes/peer/ts.json"
    )


def test_download(config, mock_boto3, tmp_path):
    from scholartools.adapters import s3_sync

    local_path = tmp_path / "out.json"
    s3_sync.download(config, "changes/peer/ts.json", local_path)
    mock_boto3.client.return_value.download_file.assert_called_once_with(
        "test-bucket", "changes/peer/ts.json", str(local_path)
    )


def test_list_keys(config, mock_boto3):
    from scholartools.adapters import s3_sync

    paginator = MagicMock()
    paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "changes/peer/t1.json"},
                {"Key": "changes/peer/t2.json"},
            ]
        },
        {},
    ]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = s3_sync.list_keys(config, "changes/")
    assert result == ["changes/peer/t1.json", "changes/peer/t2.json"]


def test_list_keys_empty(config, mock_boto3):
    from scholartools.adapters import s3_sync

    paginator = MagicMock()
    paginator.paginate.return_value = [{}]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = s3_sync.list_keys(config, "changes/")
    assert result == []


def test_exists_true(config, mock_boto3):
    from scholartools.adapters import s3_sync

    result = s3_sync.exists(config, "changes/peer/ts.json")
    assert result is True


def test_exists_false(config, mock_boto3):
    from scholartools.adapters import s3_sync

    mock_boto3.client.return_value.head_object.side_effect = Exception("not found")
    result = s3_sync.exists(config, "missing.json")
    assert result is False


def test_no_boto3_raises_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", None)
    import scholartools.adapters.s3_sync as mod

    config = SyncConfig(bucket="b", access_key="a", secret_key="s")

    def broken_import(name, *args, **kwargs):
        if name == "boto3":
            raise ImportError("No module named 'boto3'")
        return __import__(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=broken_import):
        with pytest.raises(ImportError, match="boto3 is required"):
            mod._client(config)
