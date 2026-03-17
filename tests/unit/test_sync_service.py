import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from scholartools.models import (
    ChangeLogEntry,
    LibraryCtx,
    SyncConfig,
)
from scholartools.services.sync import (
    _load_sync_state,
    _save_sync_state,
    _within_60s,
    create_snapshot,
    pull,
    push,
)


def make_ctx(tmp_path, sync_config=None, records=None):
    _records = list(records or [])

    async def read_all():
        return list(_records)

    async def write_all(r):
        _records.clear()
        _records.extend(r)

    return LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=AsyncMock(),
        delete_file=AsyncMock(),
        rename_file=AsyncMock(),
        list_file_paths=AsyncMock(return_value=[]),
        files_dir=str(tmp_path / "files"),
        api_sources=[],
        peers_dir=str(tmp_path / "peers"),
        data_dir=str(tmp_path),
        peer_id="peer-a",
        device_id="dev-1",
        sync_config=sync_config,
    ), _records


def make_sync_config():
    return SyncConfig(
        endpoint="http://localhost:9000",
        bucket="test",
        access_key="a",
        secret_key="s",
    )


def write_change_log_entry(data_dir: Path, entry: ChangeLogEntry):
    log_dir = data_dir / "change_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{entry.timestamp_hlc}.json").write_text(
        entry.model_dump_json(), encoding="utf-8"
    )


# --- helpers ---


def test_within_60s_true():
    assert _within_60s(
        "2024-01-01T00:00:00.000Z-0001-a",
        "2024-01-01T00:00:30.000Z-0001-b",
    )


def test_within_60s_false():
    assert not _within_60s(
        "2024-01-01T00:00:00.000Z-0001-a",
        "2024-01-01T00:02:00.000Z-0001-b",
    )


def test_sync_state_roundtrip(tmp_path):
    state = {"fence_push_hlc": "abc", "fence_pull_hlc": "def"}
    _save_sync_state(tmp_path, state)
    loaded = _load_sync_state(tmp_path)
    assert loaded == state


def test_load_sync_state_missing(tmp_path):
    state = _load_sync_state(tmp_path)
    assert state == {"fence_push_hlc": "", "fence_pull_hlc": ""}


# --- push ---


def test_push_no_sync_config(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=None)
    result = asyncio.run(push(ctx))
    assert result.errors
    assert "sync not configured" in result.errors[0]


def test_push_no_data_dir():
    ctx = LibraryCtx(
        read_all=AsyncMock(return_value=[]),
        write_all=AsyncMock(),
        copy_file=AsyncMock(),
        delete_file=AsyncMock(),
        rename_file=AsyncMock(),
        list_file_paths=AsyncMock(return_value=[]),
        files_dir="/tmp/files",
        api_sources=[],
        data_dir=None,
        sync_config=make_sync_config(),
    )
    result = asyncio.run(push(ctx))
    assert "data_dir not configured" in result.errors[0]


def test_push_no_keypair(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config())
    entry = ChangeLogEntry(
        op="add_reference",
        uid="uid-1",
        uid_confidence="authoritative",
        citekey="smith2020",
        data={"title": "Test"},
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc="2024-01-01T00:00:00.000Z-0001-peer-a",
        signature="",
    )
    write_change_log_entry(tmp_path, entry)

    with patch("scholartools.config.CONFIG_PATH") as mock_config_path:
        mock_key_path = MagicMock()
        mock_key_path.exists.return_value = False
        mock_config_path.parent.__truediv__ = MagicMock(
            return_value=MagicMock(__truediv__=MagicMock(return_value=mock_key_path))
        )
        result = asyncio.run(push(ctx))
    assert any("keypair" in e for e in result.errors)


def test_push_uploads_entries(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config())

    fence_entry = ChangeLogEntry(
        op="add_reference",
        uid="uid-1",
        uid_confidence="authoritative",
        citekey="smith2020",
        data={"title": "Test"},
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc="2024-01-01T00:00:01.000Z-0001-peer-a",
        signature="",
    )
    write_change_log_entry(tmp_path, fence_entry)

    privkey_bytes = b"\x00" * 32

    with (
        patch("scholartools.services.sync.CONFIG_PATH") as mcp,
        patch("scholartools.adapters.s3_sync.upload"),
    ):
        key_path = MagicMock()
        key_path.exists.return_value = True
        key_path.read_bytes.return_value = privkey_bytes
        mcp.parent.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(
                    return_value=MagicMock(__truediv__=MagicMock(return_value=key_path))
                )
            )
        )

        # patch _load_privkey directly
        with patch(
            "scholartools.services.sync._load_privkey", return_value=privkey_bytes
        ):
            result = asyncio.run(push(ctx))

    assert result.entries_pushed == 1


def test_push_updates_fence(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config())
    entry = ChangeLogEntry(
        op="add_reference",
        uid="uid-1",
        uid_confidence="",
        citekey="s2020",
        data={},
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc="2024-06-01T00:00:00.000Z-0001-peer-a",
        signature="",
    )
    write_change_log_entry(tmp_path, entry)

    with (
        patch("scholartools.services.sync._load_privkey", return_value=b"\x00" * 32),
        patch("scholartools.adapters.s3_sync.upload"),
    ):
        asyncio.run(push(ctx))

    state = _load_sync_state(tmp_path)
    assert state["fence_push_hlc"] == entry.timestamp_hlc


def test_push_upload_error_isolated(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config())
    for i in range(3):
        entry = ChangeLogEntry(
            op="add_reference",
            uid=f"uid-{i}",
            uid_confidence="",
            citekey=f"s{i}",
            data={},
            peer_id="peer-a",
            device_id="dev-1",
            timestamp_hlc=f"2024-06-01T00:00:0{i}.000Z-000{i + 1}-peer-a",
            signature="",
        )
        write_change_log_entry(tmp_path, entry)

    with (
        patch("scholartools.services.sync._load_privkey", return_value=b"\x00" * 32),
        patch(
            "scholartools.adapters.s3_sync.upload", side_effect=Exception("S3 error")
        ),
    ):
        result = asyncio.run(push(ctx))

    assert result.entries_pushed == 0
    assert len(result.errors) == 3


# --- pull ---


def test_pull_no_sync_config(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=None)
    result = asyncio.run(pull(ctx))
    assert "sync not configured" in result.errors[0]


def test_pull_applies_entries(tmp_path):
    ctx, records = make_ctx(tmp_path, sync_config=make_sync_config())
    (tmp_path / "peers").mkdir()

    entry = ChangeLogEntry(
        op="add_reference",
        uid="uid-1",
        uid_confidence="authoritative",
        citekey="smith2020",
        data={"id": "smith2020", "title": "Test", "type": "article"},
        peer_id="peer-b",
        device_id="dev-2",
        timestamp_hlc="2024-01-01T00:00:00.000Z-0001-peer-b",
        signature="valid",
    )

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            return_value=["changes/peer-b/ts.json"],
        ),
        patch("scholartools.adapters.s3_sync.download") as mock_dl,
        patch("scholartools.services.sync.load_peer_directory", return_value={}),
        patch("scholartools.services.sync.peers_service.verify_entry") as mock_verify,
    ):
        from scholartools.models import VerifyEntryResult

        mock_verify.return_value = VerifyEntryResult(verified=True)

        tmp_entry = tmp_path / "_entry.json"
        tmp_entry.write_text(entry.model_dump_json(), encoding="utf-8")

        def fake_dl(config, key, local_path):
            import shutil

            shutil.copy(str(tmp_entry), str(local_path))

        mock_dl.side_effect = fake_dl

        result = asyncio.run(pull(ctx))

    assert result.applied_count == 1
    assert result.rejected_count == 0


def test_pull_rejects_bad_signature(tmp_path):
    ctx, records = make_ctx(tmp_path, sync_config=make_sync_config())
    (tmp_path / "peers").mkdir()

    entry_dict = {
        "op": "add_reference",
        "uid": "uid-bad",
        "uid_confidence": "",
        "citekey": "bad2020",
        "data": {},
        "peer_id": "peer-x",
        "device_id": "dev-x",
        "timestamp_hlc": "2024-01-01T00:00:00.000Z-0001-peer-x",
        "signature": "invalid",
    }

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            return_value=["changes/peer-x/ts.json"],
        ),
        patch("scholartools.adapters.s3_sync.download") as mock_dl,
        patch("scholartools.services.sync.load_peer_directory", return_value={}),
        patch("scholartools.services.sync.peers_service.verify_entry") as mock_verify,
    ):
        from scholartools.models import VerifyEntryResult

        mock_verify.return_value = VerifyEntryResult(verified=False, error="bad sig")

        tmp_entry = tmp_path / "_entry.json"
        tmp_entry.write_text(json.dumps(entry_dict), encoding="utf-8")

        def fake_dl(config, key, local_path):
            import shutil

            shutil.copy(str(tmp_entry), str(local_path))

        mock_dl.side_effect = fake_dl

        result = asyncio.run(pull(ctx))

    assert result.rejected_count == 1
    rejected_dir = tmp_path / "rejected"
    assert rejected_dir.exists()


def test_pull_lww_skips_older_remote(tmp_path):
    existing = {
        "id": "s2020",
        "title": "Local Title",
        "_field_timestamps": {"title": "2024-06-01T00:00:10.000Z-0001-peer-a"},
    }
    ctx, records = make_ctx(
        tmp_path, sync_config=make_sync_config(), records=[existing]
    )
    (tmp_path / "peers").mkdir()

    entry = ChangeLogEntry(
        op="update_reference",
        uid="uid-1",
        uid_confidence="",
        citekey="s2020",
        data={"title": "Remote Title"},
        peer_id="peer-b",
        device_id="dev-2",
        timestamp_hlc="2024-06-01T00:00:05.000Z-0001-peer-b",  # older
        signature="v",
    )

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            return_value=["changes/peer-b/ts.json"],
        ),
        patch("scholartools.adapters.s3_sync.download") as mock_dl,
        patch("scholartools.services.sync.load_peer_directory", return_value={}),
        patch("scholartools.services.sync.peers_service.verify_entry") as mock_verify,
    ):
        from scholartools.models import VerifyEntryResult

        mock_verify.return_value = VerifyEntryResult(verified=True)

        tmp_entry = tmp_path / "_entry.json"
        tmp_entry.write_text(entry.model_dump_json(), encoding="utf-8")

        def fake_dl(config, key, local_path):
            import shutil

            shutil.copy(str(tmp_entry), str(local_path))

        mock_dl.side_effect = fake_dl

        asyncio.run(pull(ctx))

    assert records[0]["title"] == "Local Title"


def test_pull_conflict_within_60s(tmp_path):
    existing = {
        "id": "s2020",
        "title": "Local Title",
        "_field_timestamps": {"title": "2024-06-01T00:00:10.000Z-0001-peer-a"},
    }
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config(), records=[existing])
    (tmp_path / "peers").mkdir()

    entry = ChangeLogEntry(
        op="update_reference",
        uid="uid-1",
        uid_confidence="",
        citekey="s2020",
        data={"title": "Remote Title"},
        peer_id="peer-b",
        device_id="dev-2",
        timestamp_hlc="2024-06-01T00:00:05.000Z-0001-peer-b",  # within 60s
        signature="v",
    )

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            return_value=["changes/peer-b/ts.json"],
        ),
        patch("scholartools.adapters.s3_sync.download") as mock_dl,
        patch("scholartools.services.sync.load_peer_directory", return_value={}),
        patch("scholartools.services.sync.peers_service.verify_entry") as mock_verify,
    ):
        from scholartools.models import VerifyEntryResult

        mock_verify.return_value = VerifyEntryResult(verified=True)

        tmp_entry = tmp_path / "_entry.json"
        tmp_entry.write_text(entry.model_dump_json(), encoding="utf-8")

        def fake_dl(config, key, local_path):
            import shutil

            shutil.copy(str(tmp_entry), str(local_path))

        mock_dl.side_effect = fake_dl

        result = asyncio.run(pull(ctx))

    assert result.conflicted_count == 1
    conflicts = list((tmp_path / "conflicts").iterdir())
    assert len(conflicts) == 1


def test_pull_delete_with_local_edit_conflict(tmp_path):
    existing = {
        "id": "s2020",
        "title": "Local Title",
        "_field_timestamps": {"title": "2024-06-01T00:00:20.000Z-0001-peer-a"},
    }
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config(), records=[existing])
    (tmp_path / "peers").mkdir()

    entry = ChangeLogEntry(
        op="delete_reference",
        uid="uid-1",
        uid_confidence="",
        citekey="s2020",
        data={},
        peer_id="peer-b",
        device_id="dev-2",
        # deletion older than local edit
        timestamp_hlc="2024-06-01T00:00:10.000Z-0001-peer-b",
        signature="v",
    )

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            return_value=["changes/peer-b/ts.json"],
        ),
        patch("scholartools.adapters.s3_sync.download") as mock_dl,
        patch("scholartools.services.sync.load_peer_directory", return_value={}),
        patch("scholartools.services.sync.peers_service.verify_entry") as mock_verify,
    ):
        from scholartools.models import VerifyEntryResult

        mock_verify.return_value = VerifyEntryResult(verified=True)

        tmp_entry = tmp_path / "_entry.json"
        tmp_entry.write_text(entry.model_dump_json(), encoding="utf-8")

        def fake_dl(config, key, local_path):
            import shutil

            shutil.copy(str(tmp_entry), str(local_path))

        mock_dl.side_effect = fake_dl

        result = asyncio.run(pull(ctx))

    assert result.conflicted_count == 1


# --- snapshot ---


def test_create_snapshot(tmp_path):
    ctx, _ = make_ctx(
        tmp_path,
        sync_config=make_sync_config(),
        records=[{"id": "s2020", "type": "article"}],
    )

    with patch("scholartools.adapters.s3_sync.upload") as mock_upload:
        asyncio.run(create_snapshot(ctx))

    mock_upload.assert_called_once()
    remote_key = mock_upload.call_args[0][2]
    assert remote_key.startswith("snapshots/")
    assert remote_key.endswith(".json")


def test_create_snapshot_includes_fence_hlc(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=make_sync_config(), records=[])

    entry = ChangeLogEntry(
        op="add_reference",
        uid="uid-1",
        uid_confidence="",
        citekey="s",
        data={},
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc="2024-06-01T00:00:00.000Z-0001-peer-a",
        signature="",
    )
    log_dir = tmp_path / "change_log"
    log_dir.mkdir()
    (log_dir / f"{entry.timestamp_hlc}.json").write_text(
        entry.model_dump_json(), encoding="utf-8"
    )

    captured = {}

    def fake_upload(config, local_path, remote_key):
        with open(local_path) as f:
            captured["data"] = json.load(f)

    with patch("scholartools.adapters.s3_sync.upload", side_effect=fake_upload):
        asyncio.run(create_snapshot(ctx))

    assert captured["data"]["fence_hlc"] == entry.timestamp_hlc


def test_create_snapshot_no_sync_config(tmp_path):
    ctx, _ = make_ctx(tmp_path, sync_config=None)
    with patch("scholartools.adapters.s3_sync.upload") as mock_upload:
        asyncio.run(create_snapshot(ctx))
    mock_upload.assert_not_called()
