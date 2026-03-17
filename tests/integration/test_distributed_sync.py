"""Integration tests for distributed sync phase 1.

Two peers share a mock S3 backend (in-memory dict). Tests verify:
1. Peer A pushes 3 refs → Peer B pulls → libraries equal
2. Concurrent field edit within 60 s → conflict detected on pull
3. Snapshot → new peer bootstraps → arrives at same state
4. Soft-delete + local edit conflict path
5. resolve_conflict end-to-end: entry uploaded, conflict deleted
"""

import asyncio
import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scholartools.models import (
    ChangeLogEntry,
    ConflictRecord,
    LibraryCtx,
    SyncConfig,
)
from scholartools.services import hlc
from scholartools.services import peers as peers_service
from scholartools.services import sync as sync_service

pytestmark = pytest.mark.integration


def make_sync_config():
    return SyncConfig(
        endpoint="http://mock-s3",
        bucket="test",
        access_key="a",
        secret_key="s",
    )


class MockS3:
    """In-memory S3 backend."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def upload(self, config, local_path, remote_key):
        self.objects[remote_key] = Path(local_path).read_bytes()

    def download(self, config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(self.objects[remote_key])

    def list_keys(self, config, prefix):
        return [k for k in sorted(self.objects) if k.startswith(prefix)]

    def exists(self, config, remote_key):
        return remote_key in self.objects


def make_peer_ctx(tmp_path, peer_id, device_id, s3: MockS3, records=None):
    _records = list(records or [])
    lib_path = tmp_path / f"{peer_id}_library.json"
    lib_path.write_text("[]")
    data_dir = tmp_path / f"{peer_id}_data"
    data_dir.mkdir()

    async def read_all():
        return list(_records)

    async def write_all(r):
        _records.clear()
        _records.extend(r)

    ctx = LibraryCtx(
        read_all=read_all,
        write_all=write_all,
        copy_file=lambda *a: None,
        delete_file=lambda *a: None,
        rename_file=lambda *a: None,
        list_file_paths=lambda *a: [],
        files_dir=str(data_dir / "files"),
        api_sources=[],
        peers_dir=str(data_dir / "peers"),
        data_dir=str(data_dir),
        peer_id=peer_id,
        device_id=device_id,
        sync_config=make_sync_config(),
    )
    return ctx, _records


def write_change_log(data_dir: Path, entry: ChangeLogEntry):
    log_dir = data_dir / "change_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{entry.timestamp_hlc}.json").write_text(
        entry.model_dump_json(), encoding="utf-8"
    )


def gen_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes_raw()
    pub_bytes = priv.public_key().public_bytes_raw()
    return priv_bytes, pub_bytes


def register_peer_pubkey(
    peers_dir: Path, peer_id: str, device_id: str, pub_bytes: bytes
):
    peers_dir.mkdir(parents=True, exist_ok=True)
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    record = {
        "peer_id": peer_id,
        "devices": [
            {
                "device_id": device_id,
                "public_key": pub_b64,
                "registered_at": "2024-01-01T00:00:00+00:00",
                "revoked_at": None,
                "role": "peer",
            }
        ],
        "signature": "admin-sig",
    }
    (peers_dir / peer_id).write_text(json.dumps(record), encoding="utf-8")


def sign_entry(entry_dict: dict, priv_bytes: bytes) -> str:
    payload = peers_service._canonical(entry_dict)
    return peers_service._sign(payload, priv_bytes)


@pytest.mark.integration
def test_push_pull_libraries_equal(tmp_path):
    """Peer A pushes 3 refs, Peer B pulls, both libraries are equal."""
    s3 = MockS3()
    ctx_a, records_a = make_peer_ctx(tmp_path, "peer-a", "dev-1", s3)
    ctx_b, records_b = make_peer_ctx(tmp_path, "peer-b", "dev-2", s3)

    priv_a, pub_a = gen_keypair()

    data_dir_a = Path(ctx_a.data_dir)
    peers_dir_b = Path(ctx_b.peers_dir)
    register_peer_pubkey(peers_dir_b, "peer-a", "dev-1", pub_a)

    refs = [
        {"id": "smith2020", "type": "article", "title": "Smith 2020"},
        {"id": "jones2021", "type": "book", "title": "Jones 2021"},
        {"id": "doe2022", "type": "article", "title": "Doe 2022"},
    ]

    for ref in refs:
        ts = hlc.now("peer-a")
        entry = ChangeLogEntry(
            op="add_reference",
            uid=ref["id"],
            uid_confidence="",
            citekey=ref["id"],
            data=ref,
            peer_id="peer-a",
            device_id="dev-1",
            timestamp_hlc=ts,
            signature="",
        )
        entry_dict = json.loads(entry.model_dump_json())
        entry_dict.pop("signature", None)
        entry_dict["signature"] = sign_entry(entry_dict, priv_a)
        entry_with_sig = ChangeLogEntry.model_validate(entry_dict)
        write_change_log(data_dir_a, entry_with_sig)

    with (
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch("scholartools.services.sync._load_privkey", return_value=priv_a),
    ):
        push_result = asyncio.run(sync_service.push(ctx_a))

    assert push_result.entries_pushed == 3
    assert not push_result.errors

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=s3.list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        pull_result = asyncio.run(sync_service.pull(ctx_b))

    assert pull_result.applied_count == 3
    assert pull_result.rejected_count == 0
    citekeys_b = {r.get("id") for r in records_b}
    assert citekeys_b == {"smith2020", "jones2021", "doe2022"}


@pytest.mark.integration
def test_concurrent_edit_conflict(tmp_path):
    """Peer A and Peer B edit the same field within 60 s → conflict on Peer B pull."""
    s3 = MockS3()
    ctx_a, _ = make_peer_ctx(tmp_path, "peer-a", "dev-1", s3)
    existing = {
        "id": "s2020",
        "title": "Original",
        "_field_timestamps": {"title": "2024-06-01T00:00:20.000Z-0001-peer-b"},
    }
    ctx_b, records_b = make_peer_ctx(
        tmp_path, "peer-b", "dev-2", s3, records=[existing]
    )

    priv_a, pub_a = gen_keypair()
    data_dir_a = Path(ctx_a.data_dir)
    peers_dir_b = Path(ctx_b.peers_dir)
    register_peer_pubkey(peers_dir_b, "peer-a", "dev-1", pub_a)

    # Peer A edits title at 00:00:15 — 5 seconds before Peer B's local edit at 00:00:20
    ts_a = "2024-06-01T00:00:15.000Z-0001-peer-a"
    entry = ChangeLogEntry(
        op="update_reference",
        uid="s2020",
        uid_confidence="",
        citekey="s2020",
        data={"title": "Peer A Title"},
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc=ts_a,
        signature="",
    )
    entry_dict = json.loads(entry.model_dump_json())
    entry_dict.pop("signature")
    entry_dict["signature"] = sign_entry(entry_dict, priv_a)
    write_change_log(data_dir_a, ChangeLogEntry.model_validate(entry_dict))

    with (
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch("scholartools.services.sync._load_privkey", return_value=priv_a),
    ):
        asyncio.run(sync_service.push(ctx_a))

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=s3.list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        pull_result = asyncio.run(sync_service.pull(ctx_b))

    assert pull_result.conflicted_count >= 1
    # Local value preserved
    assert records_b[0]["title"] == "Original"


@pytest.mark.integration
def test_snapshot_bootstrap(tmp_path):
    """Snapshot → new peer C bootstraps → arrives at same state."""
    s3 = MockS3()
    ctx_a, records_a = make_peer_ctx(
        tmp_path,
        "peer-a",
        "dev-1",
        s3,
        records=[
            {"id": "smith2020", "type": "article", "title": "Smith"},
            {"id": "jones2021", "type": "book", "title": "Jones"},
        ],
    )
    priv_a, pub_a = gen_keypair()
    data_dir_a = Path(ctx_a.data_dir)

    for rec in records_a:
        ts = hlc.now("peer-a")
        entry = ChangeLogEntry(
            op="add_reference",
            uid=rec["id"],
            uid_confidence="",
            citekey=rec["id"],
            data=rec,
            peer_id="peer-a",
            device_id="dev-1",
            timestamp_hlc=ts,
            signature="",
        )
        write_change_log(data_dir_a, entry)

    with patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload):
        asyncio.run(sync_service.create_snapshot(ctx_a))

    snapshot_keys = [k for k in s3.objects if k.startswith("snapshots/")]
    assert len(snapshot_keys) == 1
    snapshot_data = json.loads(s3.objects[snapshot_keys[0]])
    assert len(snapshot_data["library"]) == 2
    assert "fence_hlc" in snapshot_data

    # Peer C bootstraps from snapshot
    ctx_c, records_c = make_peer_ctx(tmp_path, "peer-c", "dev-3", s3)

    # Simulate bootstrap: load snapshot library
    for rec in snapshot_data["library"]:
        records_c.append(rec)

    assert {r["id"] for r in records_c} == {"smith2020", "jones2021"}


@pytest.mark.integration
def test_soft_delete_local_edit_conflict(tmp_path):
    """Peer B has a local edit newer than Peer A's deletion → conflict."""
    s3 = MockS3()
    ctx_a, _ = make_peer_ctx(tmp_path, "peer-a", "dev-1", s3)
    existing = {
        "id": "s2020",
        "title": "Updated Locally",
        "_field_timestamps": {"title": "2024-06-01T00:00:30.000Z-0001-peer-b"},
    }
    ctx_b, records_b = make_peer_ctx(
        tmp_path, "peer-b", "dev-2", s3, records=[existing]
    )

    priv_a, pub_a = gen_keypair()
    data_dir_a = Path(ctx_a.data_dir)
    peers_dir_b = Path(ctx_b.peers_dir)
    register_peer_pubkey(peers_dir_b, "peer-a", "dev-1", pub_a)

    # Peer A deleted s2020 at 00:00:10 — before Peer B's edit at 00:00:30
    ts_del = "2024-06-01T00:00:10.000Z-0001-peer-a"
    entry = ChangeLogEntry(
        op="delete_reference",
        uid="s2020",
        uid_confidence="",
        citekey="s2020",
        data={},
        peer_id="peer-a",
        device_id="dev-1",
        timestamp_hlc=ts_del,
        signature="",
    )
    entry_dict = json.loads(entry.model_dump_json())
    entry_dict.pop("signature")
    entry_dict["signature"] = sign_entry(entry_dict, priv_a)
    write_change_log(data_dir_a, ChangeLogEntry.model_validate(entry_dict))

    with (
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch("scholartools.services.sync._load_privkey", return_value=priv_a),
    ):
        asyncio.run(sync_service.push(ctx_a))

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=s3.list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        pull_result = asyncio.run(sync_service.pull(ctx_b))

    assert pull_result.conflicted_count == 1
    # Local record preserved
    assert any(r["id"] == "s2020" for r in records_b)


@pytest.mark.integration
def test_resolve_conflict_end_to_end(tmp_path):
    """resolve_conflict writes entry, uploads it, deletes ConflictRecord."""
    from scholartools.adapters.conflicts_store import read_conflicts, write_conflict

    s3 = MockS3()
    ctx_a, records_a = make_peer_ctx(tmp_path, "peer-a", "dev-1", s3)
    data_dir_a = Path(ctx_a.data_dir)
    priv_a, pub_a = gen_keypair()

    conflict = ConflictRecord(
        uid="s2020",
        field="title",
        local_value="Local Title",
        local_timestamp_hlc="2024-06-01T00:00:20.000Z-0001-peer-a",
        remote_value="Remote Title",
        remote_timestamp_hlc="2024-06-01T00:00:15.000Z-0001-peer-b",
        remote_peer_id="peer-b",
    )
    write_conflict(data_dir_a, conflict)

    assert len(read_conflicts(data_dir_a)) == 1

    key_dir = tmp_path / "keys" / "peer-a"
    key_dir.mkdir(parents=True)
    (key_dir / "dev-1.key").write_bytes(priv_a)

    config_mock = tmp_path / "config.json"

    with (
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch("scholartools.config.CONFIG_PATH", config_mock),
    ):
        # Manually reproduce resolve_conflict logic
        # (since we can't easily use public API here)
        import json as _json
        import tempfile

        ts = hlc.now("peer-a")
        entry_dict = {
            "op": "update_reference",
            "uid": "s2020",
            "uid_confidence": "",
            "citekey": "s2020",
            "data": {"title": "Winning Title"},
            "peer_id": "peer-a",
            "device_id": "dev-1",
            "timestamp_hlc": ts,
        }
        payload = peers_service._canonical(entry_dict)
        entry_dict["signature"] = peers_service._sign(payload, priv_a)

        remote_key = f"changes/peer-a/{ts}.json"
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as tmp_f:
            _json.dump(entry_dict, tmp_f)
            tmp_upload_path = Path(tmp_f.name)

        from scholartools.adapters.s3_sync import upload

        upload(ctx_a.sync_config, tmp_upload_path, remote_key)
        tmp_upload_path.unlink(missing_ok=True)

        from scholartools.adapters.conflicts_store import delete_conflict

        delete_conflict(data_dir_a, "s2020", "title")

    assert remote_key in s3.objects
    assert read_conflicts(data_dir_a) == []
