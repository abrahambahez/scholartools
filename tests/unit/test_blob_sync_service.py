import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from scholartools.models import LibraryCtx, SyncConfig


def make_ctx(tmp_path, records=None, sync_config=None):
    _records = list(records or [])

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
            files_dir=str(tmp_path / "files"),
            api_sources=[],
            data_dir=str(tmp_path),
            peer_id="peer-a",
            device_id="dev-1",
            sync_config=sync_config,
        ),
        _records,
    )


def make_sync_config():
    return SyncConfig(
        endpoint="http://mock",
        bucket="test",
        access_key="a",
        secret_key="s",
    )


def write_pdf(tmp_path, name="test.pdf", content=b"pdf content"):
    p = tmp_path / name
    p.write_bytes(content)
    return p


# --- link_file tests ---


def test_link_file_missing_file(tmp_path):
    from scholartools.services.sync import link_file

    ctx, _ = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(link_file(ctx, "s2024", str(tmp_path / "missing.pdf")))
    assert not result.ok
    assert "not found" in result.error


def test_link_file_unknown_citekey(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    ctx, _ = make_ctx(tmp_path, records=[])
    result = asyncio.run(link_file(ctx, "nope", str(pdf)))
    assert not result.ok
    assert "not found" in result.error


def test_link_file_no_sync_config_sets_file_record(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    ctx, records = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(link_file(ctx, "s2024", str(pdf)))
    assert result.ok
    assert records[0].get("_file") is not None
    assert records[0]["_file"]["size_bytes"] == len(b"pdf content")
    assert records[0].get("blob_ref") is None
    assert "_field_timestamps" not in records[0] or "blob_ref" not in records[0].get(
        "_field_timestamps", {}
    )


def test_link_file_writes_change_log_with_sync(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article"}], sync_config=sync_config
    )
    with (
        patch("scholartools.adapters.s3_sync.exists", return_value=True),
        patch("scholartools.adapters.s3_sync.upload"),
        patch("scholartools.adapters.s3_sync.upload_bytes"),
    ):
        asyncio.run(link_file(ctx, "s2024", str(pdf)))
    log_files = list((tmp_path / "change_log").glob("*.json"))
    assert len(log_files) == 1
    entry = json.loads(log_files[0].read_text())
    assert entry["op"] == "link_file"
    assert entry["citekey"] == "s2024"
    assert entry["blob_ref"].startswith("sha256:")


def test_link_file_skips_upload_if_exists(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    sync_config = make_sync_config()
    ctx, records = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article"}], sync_config=sync_config
    )

    with (
        patch("scholartools.adapters.s3_sync.exists", return_value=True) as mock_exists,
        patch("scholartools.adapters.s3_sync.upload") as mock_upload,
        patch("scholartools.adapters.s3_sync.upload_bytes"),
    ):
        result = asyncio.run(link_file(ctx, "s2024", str(pdf)))

    assert result.ok
    mock_upload.assert_not_called()
    mock_exists.assert_called_once()


def test_link_file_uploads_when_absent(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article"}], sync_config=sync_config
    )

    with (
        patch("scholartools.adapters.s3_sync.exists", return_value=False),
        patch("scholartools.adapters.s3_sync.upload") as mock_upload,
        patch("scholartools.adapters.s3_sync.upload_bytes"),
    ):
        result = asyncio.run(link_file(ctx, "s2024", str(pdf)))

    assert result.ok
    mock_upload.assert_called_once()


def test_link_file_always_writes_meta(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article"}], sync_config=sync_config
    )

    with (
        patch("scholartools.adapters.s3_sync.exists", return_value=True),
        patch("scholartools.adapters.s3_sync.upload"),
        patch("scholartools.adapters.s3_sync.upload_bytes") as mock_bytes,
    ):
        result = asyncio.run(link_file(ctx, "s2024", str(pdf)))

    assert result.ok
    mock_bytes.assert_called_once()
    key_arg = mock_bytes.call_args[0][2]
    assert key_arg.endswith(".meta")


def test_link_file_entry_has_signature_when_no_privkey(tmp_path):
    from scholartools.services.sync import link_file

    pdf = write_pdf(tmp_path)
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article"}], sync_config=sync_config
    )
    with (
        patch("scholartools.services.sync._load_privkey", return_value=None),
        patch("scholartools.adapters.s3_sync.exists", return_value=True),
        patch("scholartools.adapters.s3_sync.upload"),
        patch("scholartools.adapters.s3_sync.upload_bytes"),
    ):
        result = asyncio.run(link_file(ctx, "s2024", str(pdf)))
    assert result.ok
    log_files = list((tmp_path / "change_log").glob("*.json"))
    entry = json.loads(log_files[0].read_text())
    assert entry["signature"] == ""


# --- unlink_file tests ---


def test_unlink_file_unknown_citekey(tmp_path):
    from scholartools.services.sync import unlink_file

    ctx, _ = make_ctx(tmp_path, records=[])
    result = asyncio.run(unlink_file(ctx, "nope"))
    assert not result.ok
    assert "not found" in result.error


def test_unlink_file_local_only_clears_file_record(tmp_path):
    from scholartools.services.sync import unlink_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    pdf = files_dir / "s2024.pdf"
    pdf.write_bytes(b"data")
    ctx, records = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "_file": {
                    "path": str(pdf),
                    "mime_type": "application/pdf",
                    "size_bytes": 4,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )
    result = asyncio.run(unlink_file(ctx, "s2024"))
    assert result.ok
    assert records[0].get("_file") is None
    assert not pdf.exists()
    assert not (tmp_path / "change_log").exists()


def test_unlink_file_clears_blob_ref_with_sync(tmp_path):
    from scholartools.services.sync import unlink_file

    sync_config = make_sync_config()
    ctx, records = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": "sha256:abc"}],
        sync_config=sync_config,
    )
    result = asyncio.run(unlink_file(ctx, "s2024"))
    assert result.ok
    assert records[0]["blob_ref"] is None
    assert records[0]["_field_timestamps"]["blob_ref"]


def test_unlink_file_writes_change_log_with_sync(tmp_path):
    from scholartools.services.sync import unlink_file

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": "sha256:abc"}],
        sync_config=sync_config,
    )
    asyncio.run(unlink_file(ctx, "s2024"))
    log_files = list((tmp_path / "change_log").glob("*.json"))
    assert len(log_files) == 1
    entry = json.loads(log_files[0].read_text())
    assert entry["op"] == "unlink_file"
    assert entry["blob_ref"] is None


def test_unlink_file_no_remote_delete(tmp_path):
    from scholartools.services.sync import unlink_file

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": "sha256:abc"}],
        sync_config=sync_config,
    )
    with patch("scholartools.adapters.s3_sync.upload") as mock_upload:
        asyncio.run(unlink_file(ctx, "s2024"))
    mock_upload.assert_not_called()


# --- pull link_file / unlink_file LWW tests ---


def test_pull_link_file_applies_blob_ref(tmp_path):
    from scholartools.services.sync import pull

    sha256 = "abc123"
    blob_ref = f"sha256:{sha256}"

    ctx, records = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article"}],
        sync_config=make_sync_config(),
    )
    peers_dir = tmp_path / "peers"
    peers_dir.mkdir()
    ctx = ctx.model_copy(update={"peers_dir": str(peers_dir)})

    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from scholartools.services import peers as peers_service

    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes_raw()
    pub_bytes = priv.public_key().public_bytes_raw()
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    peer_record = {
        "peer_id": "peer-b",
        "devices": [
            {
                "device_id": "dev-2",
                "public_key": pub_b64,
                "registered_at": "2024-01-01T00:00:00+00:00",
                "revoked_at": None,
                "role": "peer",
            }
        ],
        "signature": "sig",
    }
    (peers_dir / "peer-b").write_text(json.dumps(peer_record))

    ts = "2026-01-01T00:00:01.000Z-0001-peer-b"
    entry_dict = {
        "op": "link_file",
        "uid": "s2024",
        "uid_confidence": "",
        "citekey": "s2024",
        "data": {},
        "blob_ref": blob_ref,
        "peer_id": "peer-b",
        "device_id": "dev-2",
        "timestamp_hlc": ts,
        "signature": "",
    }
    payload = peers_service._canonical(entry_dict)
    entry_dict["signature"] = peers_service._sign(payload, priv_bytes)

    entry_json = json.dumps(entry_dict)

    s3_objects = {f"changes/peer-b/{ts}.json": entry_json.encode()}

    def mock_list_keys(config, prefix):
        return [k for k in s3_objects if k.startswith(prefix)]

    def mock_download(config, remote_key, local_path):
        Path(local_path).write_bytes(s3_objects[remote_key])

    with (
        patch("scholartools.adapters.s3_sync.list_keys", side_effect=mock_list_keys),
        patch("scholartools.adapters.s3_sync.download", side_effect=mock_download),
    ):
        result = asyncio.run(pull(ctx))

    assert result.applied_count >= 1
    assert records[0].get("blob_ref") == blob_ref
    assert records[0].get("_field_timestamps", {}).get("blob_ref") == ts


def test_pull_unlink_file_clears_blob_ref(tmp_path):
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from scholartools.services import peers as peers_service
    from scholartools.services.sync import pull

    ctx, records = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "blob_ref": "sha256:abc",
                "_field_timestamps": {
                    "blob_ref": "2025-01-01T00:00:00.000Z-0001-peer-x"
                },
            }
        ],
        sync_config=make_sync_config(),
    )
    peers_dir = tmp_path / "peers"
    peers_dir.mkdir()
    ctx = ctx.model_copy(update={"peers_dir": str(peers_dir)})

    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes_raw()
    pub_bytes = priv.public_key().public_bytes_raw()
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    (peers_dir / "peer-b").write_text(
        json.dumps(
            {
                "peer_id": "peer-b",
                "devices": [
                    {
                        "device_id": "dev-2",
                        "public_key": pub_b64,
                        "registered_at": "2024-01-01T00:00:00+00:00",
                        "revoked_at": None,
                        "role": "peer",
                    }
                ],
                "signature": "sig",
            }
        )
    )

    ts = "2026-01-01T00:00:01.000Z-0001-peer-b"
    entry_dict = {
        "op": "unlink_file",
        "uid": "s2024",
        "uid_confidence": "",
        "citekey": "s2024",
        "data": {},
        "blob_ref": None,
        "peer_id": "peer-b",
        "device_id": "dev-2",
        "timestamp_hlc": ts,
        "signature": "",
    }
    payload = peers_service._canonical(entry_dict)
    entry_dict["signature"] = peers_service._sign(payload, priv_bytes)

    s3_objects = {f"changes/peer-b/{ts}.json": json.dumps(entry_dict).encode()}

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            side_effect=lambda c, p: [k for k in s3_objects if k.startswith(p)],
        ),
        patch(
            "scholartools.adapters.s3_sync.download",
            side_effect=lambda c, k, lp: Path(lp).write_bytes(s3_objects[k]),
        ),
    ):
        asyncio.run(pull(ctx))

    assert records[0].get("blob_ref") is None
    assert records[0]["_field_timestamps"]["blob_ref"] == ts


def test_pull_link_file_lww_older_remote_skipped(tmp_path):
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from scholartools.services import peers as peers_service
    from scholartools.services.sync import pull

    local_ts = "2026-06-01T00:00:02.000Z-0001-peer-a"
    ctx, records = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "blob_ref": "sha256:local",
                "_field_timestamps": {"blob_ref": local_ts},
            }
        ],
        sync_config=make_sync_config(),
    )
    peers_dir = tmp_path / "peers"
    peers_dir.mkdir()
    ctx = ctx.model_copy(update={"peers_dir": str(peers_dir)})

    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes_raw()
    pub_bytes = priv.public_key().public_bytes_raw()
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    (peers_dir / "peer-b").write_text(
        json.dumps(
            {
                "peer_id": "peer-b",
                "devices": [
                    {
                        "device_id": "dev-2",
                        "public_key": pub_b64,
                        "registered_at": "2024-01-01T00:00:00+00:00",
                        "revoked_at": None,
                        "role": "peer",
                    }
                ],
                "signature": "sig",
            }
        )
    )

    old_ts = "2026-01-01T00:00:00.000Z-0001-peer-b"
    entry_dict = {
        "op": "link_file",
        "uid": "s2024",
        "uid_confidence": "",
        "citekey": "s2024",
        "data": {},
        "blob_ref": "sha256:remote",
        "peer_id": "peer-b",
        "device_id": "dev-2",
        "timestamp_hlc": old_ts,
        "signature": "",
    }
    payload = peers_service._canonical(entry_dict)
    entry_dict["signature"] = peers_service._sign(payload, priv_bytes)

    s3_objects = {f"changes/peer-b/{old_ts}.json": json.dumps(entry_dict).encode()}

    with (
        patch(
            "scholartools.adapters.s3_sync.list_keys",
            side_effect=lambda c, p: [k for k in s3_objects if k.startswith(p)],
        ),
        patch(
            "scholartools.adapters.s3_sync.download",
            side_effect=lambda c, k, lp: Path(lp).write_bytes(s3_objects[k]),
        ),
    ):
        asyncio.run(pull(ctx))

    assert records[0]["blob_ref"] == "sha256:local"


# --- get_file tests ---


def test_get_file_no_blob_ref(tmp_path):
    from scholartools.services.sync import get_file

    ctx, _ = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(get_file(ctx, "s2024"))
    assert result is None


def test_get_file_unknown_citekey(tmp_path):
    from scholartools.services.sync import get_file

    ctx, _ = make_ctx(tmp_path, records=[])
    result = asyncio.run(get_file(ctx, "nope"))
    assert result is None


def test_get_file_cache_hit(tmp_path):
    from scholartools.services.sync import get_file

    content = b"pdf bytes"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )
    cache_dir = tmp_path / "blob_cache"
    cache_dir.mkdir()
    (cache_dir / sha256).write_bytes(content)

    result = asyncio.run(get_file(ctx, "s2024"))
    assert result == cache_dir / sha256


def test_get_file_downloads_on_miss(tmp_path):
    from scholartools.services.sync import get_file

    content = b"pdf data"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(get_file(ctx, "s2024"))

    assert result is not None
    assert result.read_bytes() == content


def test_get_file_hash_mismatch_returns_none(tmp_path):
    from scholartools.services.sync import get_file

    sha256 = "deadbeef" * 8
    blob_ref = f"sha256:{sha256}"

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(b"corrupted content")

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(get_file(ctx, "s2024"))

    assert result is None


def test_get_file_corrupt_cache_redownloads(tmp_path):
    from scholartools.services.sync import get_file

    good_content = b"good pdf"
    sha256 = hashlib.sha256(good_content).hexdigest()
    blob_ref = f"sha256:{sha256}"

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )
    cache_dir = tmp_path / "blob_cache"
    cache_dir.mkdir()
    (cache_dir / sha256).write_bytes(b"corrupt data")

    def mock_download(config, remote_key, local_path):
        Path(local_path).write_bytes(good_content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(get_file(ctx, "s2024"))

    assert result is not None
    assert result.read_bytes() == good_content


# --- prefetch_blobs tests ---


def test_prefetch_blobs_no_data_dir():
    from scholartools.services.sync import prefetch_blobs

    ctx = LibraryCtx(
        read_all=lambda: asyncio.coroutine(lambda: [])(),
        write_all=lambda r: asyncio.coroutine(lambda: None)(),
        copy_file=lambda *a: None,
        delete_file=lambda *a: None,
        rename_file=lambda *a: None,
        list_file_paths=lambda *a: [],
        files_dir="/tmp",
        api_sources=[],
        data_dir=None,
    )
    result = asyncio.run(prefetch_blobs(ctx))
    assert result.errors


def test_prefetch_blobs_already_cached(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    content = b"cached"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    ctx, _ = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}]
    )
    cache_dir = tmp_path / "blob_cache"
    cache_dir.mkdir()
    (cache_dir / sha256).write_bytes(content)

    result = asyncio.run(prefetch_blobs(ctx))
    assert result.already_cached == 1
    assert result.fetched == 0
    assert not result.errors


def test_prefetch_blobs_fetches_missing(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    content = b"fresh pdf"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(prefetch_blobs(ctx))

    assert result.fetched == 1
    assert result.already_cached == 0
    assert not result.errors


def test_prefetch_blobs_filter_citekeys(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    content = b"pdf"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[
            {"id": "s2024", "type": "article", "blob_ref": blob_ref},
            {"id": "jones2020", "type": "article", "blob_ref": blob_ref},
        ],
        sync_config=sync_config,
    )
    cache_dir = tmp_path / "blob_cache"
    cache_dir.mkdir()
    (cache_dir / sha256).write_bytes(content)

    result = asyncio.run(prefetch_blobs(ctx, citekeys=["s2024"]))
    assert result.already_cached == 1
    assert result.fetched == 0


def test_prefetch_blobs_error_accumulation(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    sha256 = "a" * 64
    blob_ref = f"sha256:{sha256}"
    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )

    def mock_download(config, remote_key, local_path):
        raise OSError("network error")

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(prefetch_blobs(ctx))

    assert result.errors
    assert result.fetched == 0


def test_prefetch_blobs_skips_no_blob_ref(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    ctx, _ = make_ctx(
        tmp_path, records=[{"id": "s2024", "type": "article", "blob_ref": None}]
    )
    result = asyncio.run(prefetch_blobs(ctx))
    assert result.fetched == 0
    assert result.already_cached == 0
    assert not result.errors


# --- blob cache extension tests ---


def test_get_file_cached_path_has_extension(tmp_path):
    from scholartools.services.sync import get_file

    content = b"pdf bytes"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    meta = json.dumps({"filename": "paper.pdf"}).encode()

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if remote_key.endswith(".meta"):
            Path(local_path).write_bytes(meta)
        else:
            Path(local_path).write_bytes(content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(get_file(ctx, "s2024"))

    assert result is not None
    assert result.suffix == ".pdf"
    assert result.name == f"{sha256}.pdf"


def test_get_file_legacy_no_ext_evicted_and_replaced(tmp_path):
    from scholartools.services.sync import get_file

    content = b"pdf bytes"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    meta = json.dumps({"filename": "paper.pdf"}).encode()

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )
    cache_dir = tmp_path / "blob_cache"
    cache_dir.mkdir()
    legacy = cache_dir / sha256
    legacy.write_bytes(content)

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if remote_key.endswith(".meta"):
            Path(local_path).write_bytes(meta)
        else:
            Path(local_path).write_bytes(content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(get_file(ctx, "s2024"))

    assert not legacy.exists()
    assert result is not None
    assert result.suffix == ".pdf"


def test_prefetch_blobs_cached_path_has_extension(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    content = b"fresh pdf"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    meta = json.dumps({"filename": "doc.pdf"}).encode()

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if remote_key.endswith(".meta"):
            Path(local_path).write_bytes(meta)
        else:
            Path(local_path).write_bytes(content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(prefetch_blobs(ctx))

    assert result.fetched == 1
    cached = tmp_path / "blob_cache" / f"{sha256}.pdf"
    assert cached.exists()


def test_prefetch_blobs_legacy_no_ext_evicted_and_replaced(tmp_path):
    from scholartools.services.sync import prefetch_blobs

    content = b"cached pdf"
    sha256 = hashlib.sha256(content).hexdigest()
    blob_ref = f"sha256:{sha256}"
    meta = json.dumps({"filename": "paper.pdf"}).encode()

    sync_config = make_sync_config()
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": blob_ref}],
        sync_config=sync_config,
    )
    cache_dir = tmp_path / "blob_cache"
    cache_dir.mkdir()
    legacy = cache_dir / sha256
    legacy.write_bytes(content)

    def mock_download(config, remote_key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if remote_key.endswith(".meta"):
            Path(local_path).write_bytes(meta)
        else:
            Path(local_path).write_bytes(content)

    with patch("scholartools.adapters.s3_sync.download", side_effect=mock_download):
        result = asyncio.run(prefetch_blobs(ctx))

    assert not legacy.exists()
    assert result.fetched == 1
    assert (cache_dir / f"{sha256}.pdf").exists()


# --- attach_file tests ---


def test_attach_file_missing_path(tmp_path):
    from scholartools.services.sync import attach_file

    ctx, _ = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(attach_file(ctx, "s2024", str(tmp_path / "missing.pdf")))
    assert not result.ok
    assert "not found" in result.error


def test_attach_file_unknown_citekey(tmp_path):
    from scholartools.services.sync import attach_file

    pdf = write_pdf(tmp_path)
    ctx, _ = make_ctx(tmp_path, records=[])
    result = asyncio.run(attach_file(ctx, "nope", str(pdf)))
    assert not result.ok
    assert "not found" in result.error


def test_attach_file_outside_files_dir_copies(tmp_path):
    from scholartools.services.sync import attach_file

    pdf = write_pdf(tmp_path, name="paper.pdf")
    ctx, records = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(attach_file(ctx, "s2024", str(pdf)))
    assert result.ok
    assert records[0]["_file"]["path"] == "s2024.pdf"
    dest = tmp_path / "files" / "s2024.pdf"
    assert dest.exists()
    assert records[0].get("blob_ref") is None


def test_attach_file_inside_files_dir_no_copy(tmp_path):
    from scholartools.services.sync import attach_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    pdf = files_dir / "s2024.pdf"
    pdf.write_bytes(b"pdf content")
    ctx, records = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(attach_file(ctx, "s2024", str(pdf)))
    assert result.ok
    assert records[0]["_file"]["path"] == "s2024.pdf"
    assert list(files_dir.iterdir()) == [pdf]
    assert records[0].get("blob_ref") is None


def test_attach_file_does_not_set_blob_ref(tmp_path):
    from scholartools.services.sync import attach_file

    sync_config = make_sync_config()
    pdf = write_pdf(tmp_path)
    ctx, records = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article"}],
        sync_config=sync_config,
    )
    result = asyncio.run(attach_file(ctx, "s2024", str(pdf)))
    assert result.ok
    assert records[0].get("blob_ref") is None
    assert not (tmp_path / "change_log").exists()


# --- detach_file tests ---


def test_detach_file_synced_record_errors(tmp_path):
    from scholartools.services.sync import detach_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    pdf = files_dir / "s2024.pdf"
    pdf.write_bytes(b"data")
    ctx, _ = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "blob_ref": "sha256:abc",
                "_file": {
                    "path": "s2024.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 4,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )
    result = asyncio.run(detach_file(ctx, "s2024"))
    assert not result.ok
    assert "unsync_file" in result.error


def test_detach_file_local_only_deletes_and_clears(tmp_path):
    from scholartools.services.sync import detach_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    pdf = files_dir / "s2024.pdf"
    pdf.write_bytes(b"data")
    ctx, records = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "_file": {
                    "path": "s2024.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 4,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )
    result = asyncio.run(detach_file(ctx, "s2024"))
    assert result.ok
    assert records[0].get("_file") is None
    assert not pdf.exists()


def test_detach_file_missing_file_on_disk_still_clears(tmp_path):
    from scholartools.services.sync import detach_file

    ctx, records = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "_file": {
                    "path": "s2024.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 4,
                    "added_at": "2026-01-01T00:00:00+00:00",
                },
            }
        ],
    )
    result = asyncio.run(detach_file(ctx, "s2024"))
    assert result.ok
    assert records[0].get("_file") is None


# --- sync_file tests ---


def make_file_record(files_dir, filename="s2024.pdf", content=b"pdf content"):
    p = files_dir / filename
    files_dir.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return {
        "path": filename,
        "mime_type": "application/pdf",
        "size_bytes": len(content),
        "added_at": "2026-01-01T00:00:00+00:00",
    }


def test_sync_file_no_file_attached(tmp_path):
    from scholartools.services.sync import sync_file

    ctx, _ = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(sync_file(ctx, "s2024"))
    assert not result.ok
    assert "attach_file" in result.error


def test_sync_file_no_sync_config(tmp_path):
    from scholartools.services.sync import sync_file

    files_dir = tmp_path / "files"
    file_rec = make_file_record(files_dir)
    ctx, _ = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "_file": file_rec}],
    )
    result = asyncio.run(sync_file(ctx, "s2024"))
    assert not result.ok
    assert "sync not configured" in result.error


def test_sync_file_unknown_citekey(tmp_path):
    from scholartools.services.sync import sync_file

    ctx, _ = make_ctx(tmp_path, records=[])
    result = asyncio.run(sync_file(ctx, "nope"))
    assert not result.ok
    assert "not found" in result.error


def test_sync_file_happy_path(tmp_path):
    from scholartools.services.sync import sync_file

    files_dir = tmp_path / "files"
    file_rec = make_file_record(files_dir)
    sync_config = make_sync_config()
    ctx, records = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "_file": file_rec}],
        sync_config=sync_config,
    )

    with (
        patch("scholartools.adapters.s3_sync.exists", return_value=False),
        patch("scholartools.adapters.s3_sync.upload") as mock_upload,
        patch("scholartools.adapters.s3_sync.upload_bytes"),
    ):
        result = asyncio.run(sync_file(ctx, "s2024"))

    assert result.ok
    assert records[0]["blob_ref"].startswith("sha256:")
    assert "_field_timestamps" in records[0]
    assert "blob_ref" in records[0]["_field_timestamps"]
    mock_upload.assert_called_once()
    log_files = list((tmp_path / "change_log").glob("*.json"))
    assert len(log_files) == 1
    entry = json.loads(log_files[0].read_text())
    assert entry["op"] == "link_file"
    assert entry["citekey"] == "s2024"


def test_sync_file_s3_failure_does_not_set_blob_ref(tmp_path):
    from scholartools.services.sync import sync_file

    files_dir = tmp_path / "files"
    file_rec = make_file_record(files_dir)
    sync_config = make_sync_config()
    ctx, records = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "_file": file_rec}],
        sync_config=sync_config,
    )

    with (
        patch(
            "scholartools.adapters.s3_sync.exists",
            side_effect=OSError("connection refused"),
        ),
    ):
        result = asyncio.run(sync_file(ctx, "s2024"))

    assert not result.ok
    assert records[0].get("blob_ref") is None
    assert not (tmp_path / "change_log").exists()


# --- unsync_file tests ---


def test_unsync_file_not_synced_errors(tmp_path):
    from scholartools.services.sync import unsync_file

    ctx, _ = make_ctx(tmp_path, records=[{"id": "s2024", "type": "article"}])
    result = asyncio.run(unsync_file(ctx, "s2024"))
    assert not result.ok
    assert result.error == "file is not synced"


def test_unsync_file_not_found_errors(tmp_path):
    from scholartools.services.sync import unsync_file

    ctx, _ = make_ctx(tmp_path, records=[])
    result = asyncio.run(unsync_file(ctx, "nope"))
    assert not result.ok
    assert "not found" in result.error


def test_unsync_file_happy_path_clears_blob_ref(tmp_path):
    from scholartools.services.sync import unsync_file

    ctx, records = make_ctx(
        tmp_path,
        records=[{"id": "s2024", "type": "article", "blob_ref": "sha256:abc"}],
    )
    result = asyncio.run(unsync_file(ctx, "s2024"))
    assert result.ok
    assert "blob_ref" not in records[0]
    assert records[0]["_field_timestamps"]["blob_ref"]
    log_files = list((tmp_path / "change_log").glob("*.json"))
    assert len(log_files) == 1
    entry = json.loads(log_files[0].read_text())
    assert entry["op"] == "unlink_file"
    assert entry["citekey"] == "s2024"
    assert entry["blob_ref"] is None


def test_unsync_file_preserves_file(tmp_path):
    from scholartools.services.sync import unsync_file

    files_dir = tmp_path / "files"
    files_dir.mkdir()
    pdf = files_dir / "s2024.pdf"
    pdf.write_bytes(b"data")
    file_rec = {
        "path": str(pdf),
        "mime_type": "application/pdf",
        "size_bytes": 4,
        "added_at": "2026-01-01T00:00:00+00:00",
    }
    ctx, records = make_ctx(
        tmp_path,
        records=[
            {
                "id": "s2024",
                "type": "article",
                "blob_ref": "sha256:abc",
                "_file": file_rec,
            }
        ],
    )
    result = asyncio.run(unsync_file(ctx, "s2024"))
    assert result.ok
    assert "blob_ref" not in records[0]
    assert records[0].get("_file") == file_rec
    assert pdf.exists()
