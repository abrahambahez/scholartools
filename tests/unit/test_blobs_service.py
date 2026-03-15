import hashlib

from scholartools.services.blobs import (
    blob_cache_path,
    compute_sha256_streaming,
    ensure_blob_cache_dir,
)


def test_compute_sha256_streaming(tmp_path):
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert compute_sha256_streaming(f) == expected


def test_compute_sha256_streaming_empty(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert compute_sha256_streaming(f) == expected


def test_compute_sha256_streaming_large(tmp_path):
    data = b"x" * 200000
    f = tmp_path / "large.bin"
    f.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_sha256_streaming(f) == expected


def test_blob_cache_path(tmp_path):
    sha = "abc123def456"
    result = blob_cache_path(tmp_path, sha)
    assert result == tmp_path / "blob_cache" / sha


def test_blob_cache_path_structure(tmp_path):
    result = blob_cache_path(tmp_path, "deadbeef")
    assert result.parent == tmp_path / "blob_cache"
    assert result.name == "deadbeef"


def test_ensure_blob_cache_dir(tmp_path):
    ensure_blob_cache_dir(tmp_path)
    assert (tmp_path / "blob_cache").is_dir()


def test_ensure_blob_cache_dir_idempotent(tmp_path):
    ensure_blob_cache_dir(tmp_path)
    ensure_blob_cache_dir(tmp_path)
    assert (tmp_path / "blob_cache").is_dir()


def test_ensure_blob_cache_dir_nested(tmp_path):
    nested = tmp_path / "a" / "b"
    ensure_blob_cache_dir(nested)
    assert (nested / "blob_cache").is_dir()
