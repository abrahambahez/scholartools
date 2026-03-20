import asyncio
import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from scholartools.adapters.local import make_filestore, make_storage
from scholartools.models import LibraryCtx, SyncConfig
from scholartools.services import files as files_service
from scholartools.services import sync as sync_service

pytestmark = pytest.mark.integration


def make_ctx(tmp_path, sync_config=None):
    library_file = tmp_path / "library.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    files_dir = data_dir / "files"
    files_dir.mkdir()

    read_all, write_all = make_storage(str(library_file))
    copy_file, delete_file, rename_file, list_file_paths = make_filestore(
        str(files_dir)
    )

    return LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=copy_file,
        delete_file=delete_file,
        rename_file=rename_file,
        list_file_paths=list_file_paths,
        files_dir=str(files_dir),
        api_sources=[],
        data_dir=str(data_dir),
        peer_id="peer-a",
        device_id="dev-1",
        sync_config=sync_config,
    )


def seed_record(ctx, citekey):
    asyncio.run(ctx.write_all([{"id": citekey, "type": "article"}]))


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

    def exists(self, config, remote_key):
        return remote_key in self.objects


@pytest.mark.integration
def test_local_workflow(tmp_path):
    ctx = make_ctx(tmp_path)
    seed_record(ctx, "jones2024")

    src = tmp_path / "paper.pdf"
    src.write_bytes(b"local pdf content")

    result = asyncio.run(sync_service.attach_file(ctx, "jones2024", str(src)))
    assert result.ok

    path = asyncio.run(sync_service.get_file(ctx, "jones2024"))
    assert path is not None
    assert path.exists()
    assert path.read_bytes() == b"local pdf content"

    result = asyncio.run(sync_service.detach_file(ctx, "jones2024"))
    assert result.ok

    path = asyncio.run(sync_service.get_file(ctx, "jones2024"))
    assert path is None


@pytest.mark.integration
def test_sync_workflow(tmp_path):
    content = b"synced pdf content"
    expected_sha256 = hashlib.sha256(content).hexdigest()

    s3 = MockS3()
    ctx = make_ctx(tmp_path, sync_config=make_sync_config())
    seed_record(ctx, "smith2023")

    src = tmp_path / "paper.pdf"
    src.write_bytes(content)

    result = asyncio.run(sync_service.attach_file(ctx, "smith2023", str(src)))
    assert result.ok

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        sync_result = asyncio.run(sync_service.sync_file(ctx, "smith2023"))
        assert sync_result.ok

        records = asyncio.run(ctx.read_all())
        record = next(r for r in records if r.get("id") == "smith2023")
        assert record.get("blob_ref") == f"sha256:{expected_sha256}"

        path = asyncio.run(sync_service.get_file(ctx, "smith2023"))
        assert path is not None
        assert path.suffix == ".pdf"
        assert path.read_bytes() == content

        unsync_result = asyncio.run(sync_service.unsync_file(ctx, "smith2023"))
        assert unsync_result.ok

        records = asyncio.run(ctx.read_all())
        record = next(r for r in records if r.get("id") == "smith2023")
        assert record.get("blob_ref") is None
        assert record.get("_file") is not None

    detach_result = asyncio.run(sync_service.detach_file(ctx, "smith2023"))
    assert detach_result.ok


@pytest.mark.integration
def test_guard_sync_without_attach(tmp_path):
    ctx = make_ctx(tmp_path, sync_config=make_sync_config())
    seed_record(ctx, "brown2022")

    result = asyncio.run(sync_service.sync_file(ctx, "brown2022"))
    assert not result.ok
    assert "attach_file" in result.error


@pytest.mark.integration
def test_guard_detach_while_synced(tmp_path):
    content = b"synced pdf"
    s3 = MockS3()
    ctx = make_ctx(tmp_path, sync_config=make_sync_config())
    seed_record(ctx, "lee2021")

    src = tmp_path / "paper.pdf"
    src.write_bytes(content)

    asyncio.run(sync_service.attach_file(ctx, "lee2021", str(src)))

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
    ):
        asyncio.run(sync_service.sync_file(ctx, "lee2021"))

    result = asyncio.run(sync_service.detach_file(ctx, "lee2021"))
    assert not result.ok
    assert "unsync_file" in result.error


@pytest.mark.integration
def test_repair_workflow(tmp_path):
    ctx = make_ctx(tmp_path)
    files_dir = Path(ctx.files_dir)

    actual_file = files_dir / "garcia2020.txt"
    actual_file.write_bytes(b"repair test content")

    asyncio.run(
        ctx.write_all(
            [
                {
                    "id": "garcia2020",
                    "type": "article",
                    "_file": {
                        "path": "garcia2020.pdf",
                        "mime_type": "application/pdf",
                        "size_bytes": 19,
                        "added_at": "2024-01-01T00:00:00Z",
                    },
                }
            ]
        )
    )

    path_before = asyncio.run(sync_service.get_file(ctx, "garcia2020"))
    assert path_before is None

    reindex_result = asyncio.run(files_service.reindex_files(ctx))
    assert reindex_result.repaired == 1

    path_after = asyncio.run(sync_service.get_file(ctx, "garcia2020"))
    assert path_after is not None
    assert path_after.exists()
