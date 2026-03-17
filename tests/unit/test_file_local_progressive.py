import asyncio

from scholartools.models import LibraryCtx, SyncConfig


def make_ctx(tmp_path, records=None, sync_config=None):
    _records = list(records or [])

    async def read_all():
        return list(_records)

    async def write_all(r):
        _records.clear()
        _records.extend(r)

    files_dir = tmp_path / "files"
    files_dir.mkdir(exist_ok=True)

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
            data_dir=str(tmp_path),
            peer_id="peer-a",
            device_id="dev-1",
            sync_config=sync_config,
        ),
        _records,
        files_dir,
    )


def make_sync_config():
    return SyncConfig(
        endpoint="http://mock",
        bucket="test",
        access_key="a",
        secret_key="s",
    )


def test_link_file_local_only(tmp_path):
    from scholartools.services.sync import link_file

    src = tmp_path / "paper.pdf"
    src.write_bytes(b"pdf data")
    ctx, records, files_dir = make_ctx(
        tmp_path, records=[{"id": "smith2020", "type": "article"}]
    )

    result = asyncio.run(link_file(ctx, "smith2020", str(src)))

    assert result.ok
    assert records[0].get("_file") is not None
    assert records[0]["_file"]["size_bytes"] == len(b"pdf data")
    assert records[0]["_file"]["mime_type"] == "application/pdf"
    assert (files_dir / "smith2020.pdf").exists()
    assert records[0].get("blob_ref") is None
    assert "blob_ref" not in records[0].get("_field_timestamps", {})
    assert not (tmp_path / "change_log").exists()


def test_unlink_file_local_only(tmp_path):
    from scholartools.services.sync import unlink_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "smith2020.pdf").write_bytes(b"pdf data")

    ctx, records, _ = make_ctx(
        tmp_path,
        records=[
            {
                "id": "smith2020",
                "type": "article",
                "_file": {
                    "path": str(files_dir / "smith2020.pdf"),
                    "mime_type": "application/pdf",
                    "size_bytes": 8,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )

    result = asyncio.run(unlink_file(ctx, "smith2020"))

    assert result.ok
    assert records[0].get("_file") is None
    assert not (files_dir / "smith2020.pdf").exists()
    assert not (tmp_path / "change_log").exists()


def test_get_file_local_only(tmp_path):
    from scholartools.services.sync import get_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "smith2020.pdf").write_bytes(b"pdf data")

    ctx, _, _ = make_ctx(
        tmp_path,
        records=[
            {
                "id": "smith2020",
                "type": "article",
                "_file": {
                    "path": str(files_dir / "smith2020.pdf"),
                    "mime_type": "application/pdf",
                    "size_bytes": 8,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )

    result = asyncio.run(get_file(ctx, "smith2020"))

    assert result == files_dir / "smith2020.pdf"


def test_get_file_local_missing(tmp_path):
    from scholartools.services.sync import get_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()

    ctx, _, _ = make_ctx(
        tmp_path,
        records=[
            {
                "id": "smith2020",
                "type": "article",
                "_file": {
                    "path": str(files_dir / "smith2020.pdf"),
                    "mime_type": "application/pdf",
                    "size_bytes": 8,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )

    result = asyncio.run(get_file(ctx, "smith2020"))

    assert result is None


def test_list_files_local_only(tmp_path):
    from scholartools.services.files import list_files

    files_dir = tmp_path / "files"
    files_dir.mkdir()

    ctx, _, _ = make_ctx(
        tmp_path,
        records=[
            {
                "id": "a2024",
                "type": "article",
                "_file": {
                    "path": str(files_dir / "a2024.pdf"),
                    "mime_type": "application/pdf",
                    "size_bytes": 4,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            },
            {"id": "b2024", "type": "article"},
        ],
    )

    result = asyncio.run(list_files(ctx))

    assert result.total == 1
    assert result.files[0].citekey == "a2024"
    assert result.files[0].mime_type == "application/pdf"


def test_move_file_preserves_blob_ref(tmp_path):
    from scholartools.services.files import move_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()

    sync_config = make_sync_config()
    ctx, records, _ = make_ctx(
        tmp_path,
        records=[
            {
                "id": "smith2020",
                "type": "article",
                "blob_ref": "sha256:abc123",
                "_file": {
                    "path": str(files_dir / "smith2020.pdf"),
                    "mime_type": "application/pdf",
                    "size_bytes": 8,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
        sync_config=sync_config,
    )

    result = asyncio.run(move_file("smith2020", "smith2020_v2.pdf", ctx))

    assert result.error is None
    assert result.new_path.endswith("smith2020_v2.pdf")
    assert records[0]["blob_ref"] == "sha256:abc123"
    assert records[0]["_file"]["path"].endswith("smith2020_v2.pdf")
