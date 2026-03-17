"""Integration tests for local-file progressive enhancement (spec 011).

Tests:
1. Local-only workflow: link → get → move → list → unlink without sync_config
2. Sync workflow: link → verify file_record AND blob_ref → get returns S3 cache path
3. Mixed state: local-linked record, add sync_config, re-link → both fields populated
"""

import asyncio
import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from scholartools.models import LibraryCtx, SyncConfig
from scholartools.services import sync as sync_service
from scholartools.services.files import list_files, move_file

pytestmark = pytest.mark.integration


def make_sync_config():
    return SyncConfig(
        endpoint="http://mock-s3",
        bucket="test",
        access_key="a",
        secret_key="s",
    )


class MockS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def upload(self, config, local_path, remote_key):
        self.objects[remote_key] = Path(local_path).read_bytes()

    def upload_bytes(self, config, data: bytes, remote_key: str):
        self.objects[remote_key] = data

    def download(self, config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(self.objects[remote_key])

    def list_keys(self, config, prefix):
        return [k for k in sorted(self.objects) if k.startswith(prefix)]

    def exists(self, config, remote_key):
        return remote_key in self.objects


def make_ctx(tmp_path, records=None, sync_config=None):
    _records = list(records or [])
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    files_dir = data_dir / "files"
    files_dir.mkdir(exist_ok=True)

    async def read_all():
        return list(_records)

    async def write_all(r):
        _records.clear()
        _records.extend(r)

    return (
        LibraryCtx(
            read_all=read_all,
            write_all=write_all,
            copy_file=lambda *a: None,
            delete_file=lambda *a: None,
            rename_file=lambda *a: None,
            list_file_paths=lambda *a: [],
            files_dir=str(files_dir),
            api_sources=[],
            data_dir=str(data_dir),
            peer_id="peer-a",
            device_id="dev-1",
            sync_config=sync_config,
        ),
        _records,
        files_dir,
    )


@pytest.mark.integration
def test_local_only_full_workflow(tmp_path):
    src = tmp_path / "paper.pdf"
    src.write_bytes(b"local pdf content")

    ctx, records, files_dir = make_ctx(
        tmp_path, records=[{"id": "jones2024", "type": "article"}]
    )

    link_result = asyncio.run(sync_service.link_file(ctx, "jones2024", str(src)))
    assert link_result.ok
    assert records[0].get("_file") is not None
    assert records[0].get("blob_ref") is None
    copied_path = Path(records[0]["_file"]["path"])
    assert copied_path.exists()
    assert copied_path.read_bytes() == b"local pdf content"

    get_result = asyncio.run(sync_service.get_file(ctx, "jones2024"))
    assert get_result == copied_path

    move_result = asyncio.run(move_file("jones2024", "jones2024_v2.pdf", ctx))
    assert move_result.error is None
    new_path = Path(move_result.new_path)

    list_result = asyncio.run(list_files(ctx))
    assert list_result.total == 1
    assert list_result.files[0].citekey == "jones2024"

    unlink_result = asyncio.run(sync_service.unlink_file(ctx, "jones2024"))
    assert unlink_result.ok
    assert records[0].get("_file") is None

    list_after = asyncio.run(list_files(ctx))
    assert list_after.total == 0


@pytest.mark.integration
def test_sync_workflow_sets_both_file_record_and_blob_ref(tmp_path):
    src = tmp_path / "paper.pdf"
    content = b"synced pdf content"
    src.write_bytes(content)
    expected_sha256 = hashlib.sha256(content).hexdigest()

    s3 = MockS3()
    sync_config = make_sync_config()
    ctx, records, files_dir = make_ctx(
        tmp_path,
        records=[{"id": "jones2024", "type": "article"}],
        sync_config=sync_config,
    )

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        link_result = asyncio.run(sync_service.link_file(ctx, "jones2024", str(src)))
        assert link_result.ok
        assert records[0].get("_file") is not None
        assert records[0]["_file"]["size_bytes"] == len(content)
        assert records[0].get("blob_ref") == f"sha256:{expected_sha256}"

        get_result = asyncio.run(sync_service.get_file(ctx, "jones2024"))
        assert get_result is not None
        assert get_result.read_bytes() == content


@pytest.mark.integration
def test_mixed_state_local_then_sync(tmp_path):
    src = tmp_path / "paper.pdf"
    content = b"mixed state pdf"
    src.write_bytes(content)
    expected_sha256 = hashlib.sha256(content).hexdigest()

    ctx, records, files_dir = make_ctx(
        tmp_path, records=[{"id": "jones2024", "type": "article"}]
    )

    local_result = asyncio.run(sync_service.link_file(ctx, "jones2024", str(src)))
    assert local_result.ok
    assert records[0].get("_file") is not None
    assert records[0].get("blob_ref") is None

    s3 = MockS3()
    sync_config = make_sync_config()
    ctx_synced = ctx.model_copy(update={"sync_config": sync_config})

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
    ):
        relink_result = asyncio.run(
            sync_service.link_file(ctx_synced, "jones2024", str(src))
        )

    assert relink_result.ok
    assert records[0].get("_file") is not None
    assert records[0].get("blob_ref") == f"sha256:{expected_sha256}"
    assert f"blobs/{expected_sha256}" in s3.objects
