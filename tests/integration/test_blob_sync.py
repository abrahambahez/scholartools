"""Integration tests for blob sync (feat 009).

Two-peer MockS3 backend verifies:
1. link_file → uploaded once, blob exists on S3
2. pull → record has blob_ref, no local file downloaded
3. get_file → downloads, verifies sha256, returns cache path
4. link_file same content → no re-upload (HEAD → 200)
5. prefetch_blobs(citekeys) → fetched=1
6. prefetch_blobs() → already_cached=1
7. unlink_file → blob untouched on remote
8. pull after unlink → blob_ref cleared via LWW
9. corrupt cache → get_file re-fetches, surfaces mismatch error
10. LWW conflict → newer timestamp_hlc wins
"""

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scholartools.models import ChangeLogEntry, LibraryCtx, SyncConfig
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


def make_peer_ctx(tmp_path, peer_id, device_id, records=None):
    _records = list(records or [])
    data_dir = tmp_path / f"{peer_id}_data"
    data_dir.mkdir(exist_ok=True)

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
        admin_peer_id=peer_id,
        admin_device_id=device_id,
        sync_config=make_sync_config(),
    )
    return ctx, _records


def gen_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    return priv.private_bytes_raw(), priv.public_key().public_bytes_raw()


def register_peer(peers_dir: Path, peer_id: str, device_id: str, pub_bytes: bytes):
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


def write_change_log(data_dir: Path, entry: ChangeLogEntry):
    log_dir = data_dir / "change_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{entry.timestamp_hlc}.json").write_text(
        entry.model_dump_json(), encoding="utf-8"
    )


def sign_entry(entry_dict: dict, priv_bytes: bytes) -> str:
    payload = peers_service._canonical(entry_dict)
    return peers_service._sign(payload, priv_bytes)


def push_signed_change_log(ctx: LibraryCtx, s3: MockS3, priv_bytes: bytes):
    data_dir = Path(ctx.data_dir)
    from scholartools.services.sync import _change_log_entries

    entries = _change_log_entries(data_dir, "")
    for _, entry in entries:
        entry_dict = json.loads(entry.model_dump_json())
        entry_dict.pop("signature", None)
        entry_dict["signature"] = sign_entry(entry_dict, priv_bytes)
        key = f"changes/{ctx.admin_peer_id}/{entry.timestamp_hlc}.json"
        s3.objects[key] = json.dumps(entry_dict).encode()


@pytest.mark.integration
def test_link_file_uploaded_once(tmp_path):
    """Peer A link_file → blob uploaded to S3 exactly once."""
    s3 = MockS3()
    ctx_a, records_a = make_peer_ctx(
        tmp_path, "peer-a", "dev-1", [{"id": "smith2024", "type": "article"}]
    )

    pdf = tmp_path / "smith2024.pdf"
    pdf.write_bytes(b"pdf content")
    sha256 = hashlib.sha256(b"pdf content").hexdigest()

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
        patch("scholartools.services.sync._load_privkey", return_value=None),
    ):
        result = asyncio.run(sync_service.link_file(ctx_a, "smith2024", str(pdf)))

    assert result.ok
    assert f"blobs/{sha256}" in s3.objects
    assert f"blobs/{sha256}.meta" in s3.objects
    assert records_a[0]["blob_ref"] == f"sha256:{sha256}"


@pytest.mark.integration
def test_pull_receives_blob_ref_no_download(tmp_path):
    """Peer B pull → record has blob_ref; no blob downloaded."""
    s3 = MockS3()
    ctx_a, records_a = make_peer_ctx(
        tmp_path, "peer-a", "dev-1", [{"id": "smith2024", "type": "article"}]
    )
    ctx_b, records_b = make_peer_ctx(
        tmp_path, "peer-b", "dev-2", [{"id": "smith2024", "type": "article"}]
    )

    priv_a, pub_a = gen_keypair()
    register_peer(Path(ctx_b.peers_dir), "peer-a", "dev-1", pub_a)

    pdf = tmp_path / "smith2024.pdf"
    pdf.write_bytes(b"pdf bytes")
    sha256 = hashlib.sha256(b"pdf bytes").hexdigest()

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=s3.upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
        patch("scholartools.services.sync._load_privkey", return_value=priv_a),
    ):
        asyncio.run(sync_service.link_file(ctx_a, "smith2024", str(pdf)))

    push_signed_change_log(ctx_a, s3, priv_a)

    download_called = []

    def tracking_download(config, remote_key, local_path):
        download_called.append(remote_key)
        s3.download(config, remote_key, local_path)

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=s3.list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=tracking_download),
    ):
        asyncio.run(sync_service.pull(ctx_b))

    assert records_b[0].get("blob_ref") == f"sha256:{sha256}"
    blob_downloads = [k for k in download_called if k.startswith("blobs/")]
    assert blob_downloads == []


@pytest.mark.integration
def test_get_file_downloads_and_caches(tmp_path):
    """Peer B get_file → downloads, verifies sha256, returns cache path."""
    s3 = MockS3()
    content = b"the actual pdf"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    s3.objects[f"blobs/{sha256}"] = content

    ctx_b, _ = make_peer_ctx(
        tmp_path,
        "peer-b",
        "dev-2",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    with patch("scholartools.adapters.s3_sync.download", side_effect=s3.download):
        result = asyncio.run(sync_service.get_file(ctx_b, "smith2024"))

    assert result is not None
    assert result.read_bytes() == content


@pytest.mark.integration
def test_link_file_same_content_no_reupload(tmp_path):
    """Peer A link_file same content twice → second call skips upload."""
    s3 = MockS3()
    ctx_a, _ = make_peer_ctx(
        tmp_path, "peer-a", "dev-1", [{"id": "smith2024", "type": "article"}]
    )

    pdf = tmp_path / "smith2024.pdf"
    pdf.write_bytes(b"same content")

    upload_calls = []

    def tracking_upload(config, local_path, remote_key):
        upload_calls.append(remote_key)
        s3.upload(config, local_path, remote_key)

    with (
        patch("scholartools.adapters.s3_sync.exists", side_effect=s3.exists),
        patch("scholartools.adapters.s3_sync.upload", side_effect=tracking_upload),
        patch(
            "scholartools.adapters.s3_sync.upload_bytes", side_effect=s3.upload_bytes
        ),
        patch("scholartools.services.sync._load_privkey", return_value=None),
    ):
        asyncio.run(sync_service.link_file(ctx_a, "smith2024", str(pdf)))
        asyncio.run(sync_service.link_file(ctx_a, "smith2024", str(pdf)))

    blob_uploads = [
        k for k in upload_calls if k.startswith("blobs/") and not k.endswith(".meta")
    ]
    assert len(blob_uploads) == 1


@pytest.mark.integration
def test_prefetch_blobs_fetched(tmp_path):
    """Peer C prefetch_blobs(["smith2024"]) → fetched=1."""
    s3 = MockS3()
    content = b"blob for prefetch"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    s3.objects[f"blobs/{sha256}"] = content

    ctx_c, _ = make_peer_ctx(
        tmp_path,
        "peer-c",
        "dev-3",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    with patch("scholartools.adapters.s3_sync.download", side_effect=s3.download):
        result = asyncio.run(sync_service.prefetch_blobs(ctx_c, ["smith2024"]))

    assert result.fetched == 1
    assert result.already_cached == 0
    assert not result.errors


@pytest.mark.integration
def test_prefetch_blobs_already_cached(tmp_path):
    """Peer B prefetch_blobs() after get_file → already_cached=1."""
    s3 = MockS3()
    content = b"cached blob"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    s3.objects[f"blobs/{sha256}"] = content

    ctx_b, _ = make_peer_ctx(
        tmp_path,
        "peer-b",
        "dev-2",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    with patch("scholartools.adapters.s3_sync.download", side_effect=s3.download):
        asyncio.run(sync_service.get_file(ctx_b, "smith2024"))
        result = asyncio.run(sync_service.prefetch_blobs(ctx_b))

    assert result.already_cached == 1
    assert result.fetched == 0


@pytest.mark.integration
def test_unlink_file_blob_untouched(tmp_path):
    """Peer A unlink_file → blob remains on S3."""
    s3 = MockS3()
    content = b"persistent blob"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    s3.objects[f"blobs/{sha256}"] = content

    ctx_a, _ = make_peer_ctx(
        tmp_path,
        "peer-a",
        "dev-1",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    with patch("scholartools.services.sync._load_privkey", return_value=None):
        asyncio.run(sync_service.unlink_file(ctx_a, "smith2024"))

    assert f"blobs/{sha256}" in s3.objects


@pytest.mark.integration
def test_pull_after_unlink_clears_blob_ref(tmp_path):
    """Peer B pull after Peer A unlink → blob_ref cleared via LWW."""
    s3 = MockS3()
    content = b"will be unlinked"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"

    ctx_a, records_a = make_peer_ctx(
        tmp_path,
        "peer-a",
        "dev-1",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )
    ctx_b, records_b = make_peer_ctx(
        tmp_path,
        "peer-b",
        "dev-2",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    priv_a, pub_a = gen_keypair()
    register_peer(Path(ctx_b.peers_dir), "peer-a", "dev-1", pub_a)

    with patch("scholartools.services.sync._load_privkey", return_value=priv_a):
        asyncio.run(sync_service.unlink_file(ctx_a, "smith2024"))

    push_signed_change_log(ctx_a, s3, priv_a)

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=s3.list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        asyncio.run(sync_service.pull(ctx_b))

    assert records_b[0].get("blob_ref") is None


@pytest.mark.integration
def test_corrupt_cache_get_file_redownloads(tmp_path):
    """Corrupt cache → get_file re-fetches and returns None on mismatch."""
    s3 = MockS3()
    good_content = b"good pdf"
    sha256 = hashlib.sha256(good_content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    s3.objects[f"blobs/{sha256}"] = good_content

    ctx_b, _ = make_peer_ctx(
        tmp_path,
        "peer-b",
        "dev-2",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    data_dir = Path(ctx_b.data_dir)
    cache_dir = data_dir / "blob_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / sha256).write_bytes(b"this is corrupt")

    with patch("scholartools.adapters.s3_sync.download", side_effect=s3.download):
        result = asyncio.run(sync_service.get_file(ctx_b, "smith2024"))

    assert result is not None
    assert result.read_bytes() == good_content


@pytest.mark.integration
def test_corrupt_cache_hash_mismatch_surfaces_error(tmp_path):
    """When download itself is corrupt → get_file returns None (no raise)."""
    s3 = MockS3()
    sha256 = "a" * 64
    blob_ref = f"sha256:{sha256}"
    s3.objects[f"blobs/{sha256}"] = b"completely wrong data"

    ctx_b, _ = make_peer_ctx(
        tmp_path,
        "peer-b",
        "dev-2",
        [{"id": "smith2024", "type": "article", "blob_ref": blob_ref}],
    )

    with patch("scholartools.adapters.s3_sync.download", side_effect=s3.download):
        result = asyncio.run(sync_service.get_file(ctx_b, "smith2024"))

    assert result is None


@pytest.mark.integration
def test_lww_conflict_newer_wins(tmp_path):
    """Two peers link different files → peer with newer timestamp wins on pull."""
    s3 = MockS3()
    content_a = b"peer a pdf"
    sha256_a = hashlib.sha256(content_a).hexdigest()
    content_b = b"peer b pdf"
    sha256_b = hashlib.sha256(content_b).hexdigest()

    priv_a, pub_a = gen_keypair()
    priv_b, pub_b = gen_keypair()

    ts_older = "2026-01-01T10:00:00.000Z-0001-peer-a"
    ts_newer = "2026-01-01T12:00:00.000Z-0001-peer-b"

    shared_record = {"id": "smith2024", "type": "article"}
    ctx_c, records_c = make_peer_ctx(tmp_path, "peer-c", "dev-3", [dict(shared_record)])
    peers_dir_c = Path(ctx_c.peers_dir)
    register_peer(peers_dir_c, "peer-a", "dev-1", pub_a)
    register_peer(peers_dir_c, "peer-b", "dev-2", pub_b)

    for peer_id, device_id, sha256, ts, priv_bytes in [
        ("peer-a", "dev-1", sha256_a, ts_older, priv_a),
        ("peer-b", "dev-2", sha256_b, ts_newer, priv_b),
    ]:
        entry_dict = {
            "op": "link_file",
            "uid": "smith2024",
            "uid_confidence": "",
            "citekey": "smith2024",
            "data": {},
            "blob_ref": f"sha256:{sha256}",
            "peer_id": peer_id,
            "device_id": device_id,
            "timestamp_hlc": ts,
            "signature": "",
        }
        payload = peers_service._canonical(entry_dict)
        entry_dict["signature"] = peers_service._sign(payload, priv_bytes)
        s3.objects[f"changes/{peer_id}/{ts}.json"] = json.dumps(entry_dict).encode()

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=s3.list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=s3.download),
    ):
        asyncio.run(sync_service.pull(ctx_c))

    assert records_c[0].get("blob_ref") == f"sha256:{sha256_b}"
