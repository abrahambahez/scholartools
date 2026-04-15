# 009: blob sync — content-addressed file distribution over S3

> **Superseded in part by feat 021 (v0.11.0):** `link_file` and `unlink_file` were replaced
> by `attach_file` / `detach_file` (local ops) + `sync_file` / `unsync_file` (S3 ops).
> The blob storage format and sha256 content-addressing described here remain accurate;
> the public API surface for triggering uploads has changed. See `docs/feats/021-file-management-refactor.md`.

## context

Full design rationale is in `docs/rfc/001-distributed-sync.md` (phase 2 section).
Phase 1 (feat 008) syncs reference metadata only — PDFs and other linked files remain
local. This feat adds the blob layer: lazy on-demand file distribution using
content-addressed storage over the same S3-compatible backend.

Prerequisites: feat 008 (`passes: true`).

## what changes

### storage layout

Phase 2 adds one new prefix to the shared bucket:

```
{shared-root}/
    blobs/{sha256}        ← raw file, key is its hex sha256
    blobs/{sha256}.meta   ← small JSON sidecar for human readability
```

The sha256 is the identity. Deduplication is free: two peers uploading the same PDF
produce the same key and the second upload is skipped via HEAD check.

The `.meta` sidecar is written alongside the blob on every `link_file` and re-uploaded
on citekey rename (cheap — typically < 200 bytes). It contains:

```json
{
  "citekey": "perez2024",
  "filename": "perez2024.pdf",
  "uploaded_by": "scholar-abc",
  "timestamp_hlc": "2026-03-14T10:05:00.000Z-0001-scholar-abc"
}
```

Auditing the bucket: list `blobs/*.meta` to get a human-readable index of citekey →
sha256 mappings. Validation never reads `.meta` — integrity is always verified against
the sha256 of the downloaded blob content.

**One canonical file per reference.** `blob_ref` is a single field on the record. If two
peers link different files to the same citekey, LWW applies — the entry with the greater
`timestamp_hlc` wins. The losing blob remains in the bucket (orphaned, harmless) and its
`.meta` is never re-linked. Scholars coordinate which file is canonical the same way they
resolve any other field conflict.

### new change log ops (`models.py`)

Two new ops extend `ChangeLogEntry.op`:

```python
op: Literal[
    "add_reference", "update_reference", "delete_reference", "restore_reference",
    "link_file", "unlink_file",
]
```

`link_file` entry shape:

```json
{
  "op": "link_file",
  "uid": "a3f9c2d1",
  "blob_ref": "sha256:e3b0c44298fc1c149afbf4c8996fb924",
  "peer_id": "scholar-abc",
  "device_id": "laptop-primary",
  "timestamp_hlc": "2026-03-11T10:05:00.000Z-0001-scholar-abc",
  "signature": "<base64 Ed25519>"
}
```

`unlink_file` has the same shape. No `data` field — the blob content is never in the
change log, only the content address.

New field on `Reference` model:

```python
blob_ref: str | None = None   # "sha256:{hex}" or None
```

`_field_timestamps` already tracks per-field LWW — `blob_ref` is a plain field and
participates in the same LWW as any other field.

### `link_file` upload flow (`services/sync.py`)

> **Renamed in v0.11.0:** `link_file` is replaced by `attach_file` (local copy) + `sync_file` (S3 upload). The upload logic described below now lives in `sync_file`.

`link_file(citekey, path) → Result` (original design — see feat 021 for current API):

1. Hash local file → `sha256` (streaming, no full read into memory)
2. `s3_sync.exists(config, f"blobs/{sha256}")` — skip upload if already present
3. `s3_sync.upload(config, path, f"blobs/{sha256}")` — only if absent
4. Write sidecar: `s3_sync.upload_bytes(config, meta_json, f"blobs/{sha256}.meta")` — always overwrite (cheap, ensures latest citekey)
5. Write `link_file` change log entry with `blob_ref: f"sha256:{sha256}"`
6. Update local record's `blob_ref` field + `_field_timestamps`

This is the only place a blob is uploaded. `push_changelog()` does not re-upload blobs — the
change log entry is enough for other peers to know the sha256 exists.

### lazy `get_file` (`services/sync.py` or `services/library.py`)

`get_file(citekey) → Path | None` gains an `ensure_local()` step:

1. Load record, check `blob_ref`
2. If `blob_ref` is None → return None
3. Compute local cache path: `{data_dir}/blob_cache/{sha256}`
4. If path exists → return it (already cached)
5. `s3_sync.download(config, f"blobs/{sha256}", cache_path)` → return cache_path

The local file link path (`file` field on the record) is replaced with the cache path on
first successful fetch. Subsequent calls are cache hits.

### `prefetch_blobs` (`services/sync.py`)

`prefetch_blobs(citekeys: list[str] | None = None) → PrefetchResult` downloads all
referenced blobs for the given citekeys (or all records if `None`):

1. Load all records matching citekeys filter
2. For each record with a non-None `blob_ref` and missing local cache file: download
3. Return `PrefetchResult(fetched, already_cached, errors)`

Designed for offline-before-fieldwork use. Large libraries: O(n) HEAD checks before
download; only missing blobs are fetched.

New model:

```python
class PrefetchResult(BaseModel):
    fetched: int
    already_cached: int
    errors: list[str]
```

### `unlink_file` flow

> **Renamed in v0.11.0:** `unlink_file` is replaced by `unsync_file` (clears blob_ref, writes log) + `detach_file` (deletes local copy). See feat 021.

`unlink_file(citekey) → Result` (original design):

1. Write `unlink_file` change log entry
2. Clear `blob_ref` from local record
3. Does NOT delete the blob from remote — blob storage is append-only by design

Local cache file is not deleted — another record on the same peer may still reference the
same sha256.

### `pull_changelog()` changes (non-breaking, renamed from `pull()` in v0.12.0)

`pull_changelog()` already replays all change log ops by type. Two new branches:

- `link_file`: apply `blob_ref` to local record via LWW (same as any field update); do
  **not** download the file — lazy fetch on `get_file` demand
- `unlink_file`: clear `blob_ref` via LWW

No blob content is transferred during pull-changelog. Pull stays lightweight regardless of how
many PDFs the shared index contains.

### blob cache layout (`config.py` / `Settings`)

Cache directory: `{data_dir}/blob_cache/` — created on first write, no config needed.

> **Changed in v0.11.0:** files are now named `{sha256}{ext}` (e.g. `e3b0c44….pdf`), not bare sha256. The extension is fetched from the `.meta` sidecar on download. Legacy no-extension cache files are evicted and re-downloaded on next access.

Not tracked by the change log.

Cache is local and disposable — peers can delete the entire directory and rebuild on next
`get_file` or `prefetch_blobs`.

### S3 adapter (`adapters/s3_sync.py`)

One new function required:

- `upload_bytes(config, data: bytes, remote_key: str)` — uploads in-memory bytes; used
  for `.meta` sidecars without writing a temp file

`upload`, `download`, `exists` already cover blob operations. All blob keys use the same
`RemoteSyncPort` interface as change log keys.

### public API (`__init__.py`)

> **Updated in v0.11.0:** see feat 021 for the current public API. The functions below were the original design.

Original functions (v0.9.x):
- `link_file(citekey, path)` — hash + conditional S3 upload + set blob_ref (now: `sync_file`)
- `get_file(citekey)` — lazy fetch from S3 cache (unchanged signature)
- `prefetch_blobs(citekeys: list[str] | None = None) → PrefetchResult` (unchanged)

Added in v0.11.0:
- `upload_blobs() → UploadBlobsResult` — bulk-upload all locally attached files that lack `blob_ref`

## design decisions

**Lazy by default.** `pull_changelog()` never fetches blob content. Daily sync stays fast for
scholars who work primarily with metadata. Blobs arrive only when a file is opened or
`prefetch_blobs` is called explicitly.

**Content-addressed, not path-addressed.** Two peers uploading the same PDF produce the
same key. No dedup logic needed — HEAD check before upload is sufficient.

**One canonical file per reference.** `blob_ref` is a single `str | None` field.
Multiple peers linking different files to the same citekey resolve via LWW — the newer
`timestamp_hlc` wins. This is consistent with how all other reference fields behave and
avoids the complexity of set-union merge semantics.

**`.meta` sidecar for auditability.** Blob objects are named by sha256 only for
integrity. The `.meta` companion makes the bucket human-readable without affecting
validation. Sidecar is always overwritten on `link_file` — no versioning needed since
`blob_ref` LWW already determines which sha256 is current.

**Append-only blob storage.** Blobs are never deleted from remote. `unlink_file` removes
the association in the change log but the blob stays in the bucket. Storage cleanup is
operator responsibility via S3 lifecycle policies (as with change log files).

**No blob signing.** Blob content is verified implicitly via sha256: if
`sha256(downloaded_file) != stored_sha256`, discard and surface as error. No Ed25519
signature on the blob object itself. The `link_file` change log entry is signed and
carries the expected sha256, so the trust chain is: signed entry → sha256 → blob
content.

**No Garage adapter in this feat.** Garage integration (federated cluster deployment) is
a separate feat. The `RemoteSyncPort` interface is already designed to accommodate it.

## out of scope

- Garage federated adapter — separate feat
- Blob access control per peer — S3 bucket policies / ACLs, operator responsibility
- Automatic cache eviction — not in scope; manual deletion or S3 lifecycle rules
- Encrypted blobs at rest — operator responsibility (S3 server-side encryption)
- Versioned blobs — content-addressed storage is inherently immutable per sha256
- Streaming upload for very large files — standard boto3 multipart is sufficient for
  academic PDFs; streaming optimisation deferred
