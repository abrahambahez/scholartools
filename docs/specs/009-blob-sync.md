# spec: 009-blob-sync

## findings

From `docs/feats/009-blob-sync.md`:

Phase 2 of distributed sync adds content-addressed blob storage over the same
S3-compatible backend used by Phase 1 (feat 008). PDFs and other linked files are stored
by their sha256 hash, deduplicating transparently across peers. The change log gains two
new operations: `link_file` and `unlink_file`, which record the content address in a new
`blob_ref` field on Reference models.

Key design decisions:
- **Lazy by default**: `pull()` never fetches blob content; files arrive on-demand via
  `get_file()` or explicit `prefetch_blobs()` call
- **Content-addressed**: two peers uploading the same file produce the same key; dedup
  is free via HEAD check before upload
- **One canonical file per reference**: `blob_ref` is a single `str | None` field;
  multiple peers linking different files resolve via LWW on `timestamp_hlc`
- **`.meta` sidecars for auditability**: each blob has a small JSON companion listing
  citekey, filename, uploader, and timestamp (no validation dependency)
- **Append-only blobs**: deleted blobs remain in storage; `unlink_file` only updates the
  change log
- **No blob signing**: integrity verified implicitly via sha256; signed `link_file` entry
  carries the expected hash

Storage layout:

```
{shared-root}/
    blobs/{sha256}        ← raw file
    blobs/{sha256}.meta   ← human-readable sidecar JSON
```

Local cache directory: `{data_dir}/blob_cache/{sha256}` (disposable, rebuilt on demand).

## objective

Agents gain transparent, lazy on-demand access to shared PDF and file archives across
peers via content-addressed storage. `link_file()` uploads files to S3, `get_file()`
fetches them on-demand with local caching, and `prefetch_blobs()` allows offline
preparation before fieldwork. The change log tracks all blob operations (`link_file`,
`unlink_file`) with cryptographic signatures; pull replicates metadata without
transferring file content.

## acceptance criteria

- WHEN an agent calls `link_file(citekey, local_path)` THEN the system computes the
  file's sha256 (streaming, no full memory load), checks if `blobs/{sha256}` exists on
  remote via HEAD, uploads the file only if absent, writes a `blobs/{sha256}.meta`
  sidecar with citekey/filename/uploader/timestamp_hlc, appends a signed `link_file`
  change log entry, updates the local record's `blob_ref` and `_field_timestamps`, and
  returns `Result` — never raises.

- WHEN two peers upload the same file THEN the second upload is skipped (HEAD → 200);
  the `.meta` sidecar is rewritten with the caller's citekey; no duplicate blob storage
  occurs.

- WHEN an agent calls `pull()` THEN `link_file` entries apply `blob_ref` to the local
  record via LWW (lexicographic `timestamp_hlc` comparison); `unlink_file` entries clear
  `blob_ref` via LWW; no blob file is downloaded during pull.

- WHEN an agent calls `unlink_file(citekey)` THEN the system writes a signed
  `unlink_file` entry to the change log, clears `blob_ref` from the local record, does
  NOT delete the blob from remote, and returns `Result` — never raises.

- WHEN an agent calls `get_file(citekey)` THEN the system returns None if `blob_ref` is
  None, returns the cache path if `{data_dir}/blob_cache/{sha256}` exists (cache hit),
  otherwise downloads from `blobs/{sha256}`, verifies `sha256(downloaded) == stored_sha256`
  (discards and surfaces error if mismatch), and returns the cache path — never raises on
  success.

- WHEN an agent calls `prefetch_blobs(citekeys=None)` THEN the system loads all matching
  records (all if None), downloads and verifies each blob with a missing cache file, and
  returns `PrefetchResult(fetched, already_cached, errors)` — never raises.

- WHEN two peers link different files to the same citekey THEN `pull()` applies LWW:
  the entry with the greater `timestamp_hlc` wins; the losing blob remains in storage
  orphaned; its `.meta` is never re-linked.

- WHEN the local cache file is deleted THEN `get_file()` re-downloads on next call and
  recovers without error.

- WHEN `config.json` has no sync block THEN `link_file`, `get_file`, and
  `prefetch_blobs` operate on the local filesystem only; no S3 calls occur.

## tasks

- [x] task-01: extend models (`models.py`) — blocks: none
  - Extend `ChangeLogEntry.op` enum: add `"link_file"`, `"unlink_file"`
  - Add `blob_ref: str | None = None` to `Reference`
  - Add `PrefetchResult(BaseModel)`: `fetched: int`, `already_cached: int`, `errors: list[str]`
  - Unit tests: model validation, serialization round-trips

- [x] task-02: `upload_bytes()` in `adapters/s3_sync.py` — blocks: none
  - `upload_bytes(config: SyncConfig, data: bytes, remote_key: str) -> None`
  - uploads in-memory bytes without temp file; used for `.meta` sidecars
  - unit tests: mocked boto3 `put_object`, data transmission

- [x] task-03: `services/blobs.py` — blob hashing and cache paths — blocks: task-01
  - `compute_sha256_streaming(path: Path) -> str`
  - `blob_cache_path(data_dir: Path, sha256: str) -> Path`
  - `ensure_blob_cache_dir(data_dir: Path)`
  - unit tests: hash correctness, path generation, directory creation

- [x] task-04: `link_file` in `services/sync.py` — blocks: task-02, task-03
  - `async def link_file(ctx: LibraryCtx, citekey: str, local_path: str) -> Result`
  - hash → HEAD check → conditional upload → meta sidecar → signed change log entry →
    update record `blob_ref` + `_field_timestamps`
  - unit tests: skip upload if present, meta overwrite, entry signing, record update

- [x] task-05: `unlink_file` in `services/sync.py` — blocks: task-04
  - `async def unlink_file(ctx: LibraryCtx, citekey: str) -> Result`
  - signed `unlink_file` entry → clear `blob_ref` → update `_field_timestamps`
  - does NOT delete blob from remote
  - unit tests: entry creation, record clearing, no remote delete call

- [x] task-06: extend `pull()` in `services/sync.py` — blocks: task-04, task-05
  - add `link_file` and `unlink_file` branches to pull's replay switch
  - both apply via LWW; no blob download
  - unit tests: LWW application, timestamp tracking, no download side-effect

- [x] task-07: lazy `get_file` in `services/library.py` — blocks: task-03
  - `async def get_file(ctx: LibraryCtx, citekey: str) -> Path | None`
  - None → return None; cache hit → return path; miss → download → verify sha256 →
    cache → return path; mismatch → error
  - unit tests: None path, cache hit, download + verify, hash mismatch error

- [x] task-08: `prefetch_blobs` in `services/sync.py` — blocks: task-07
  - `async def prefetch_blobs(ctx: LibraryCtx, citekeys: list[str] | None = None) -> PrefetchResult`
  - filter records, download missing blobs, verify sha256, accumulate counts
  - unit tests: filtering, cache existence check, error accumulation

- [x] task-09: wire into public API (`__init__.py`) — blocks: task-04, task-05, task-08
  - `link_file(citekey: str, path: str) -> Result`
  - `get_file(citekey: str) -> Path | None`
  - `prefetch_blobs(citekeys: list[str] | None = None) -> PrefetchResult`
  - all sync wrappers via `asyncio.run()`
  - unit tests: wrapper invocation, return value passthrough

- [x] task-10: integration tests — blocks: task-09
  - two-peer MockS3 backend
  - peer A: `link_file("smith2024", "local.pdf")` → uploaded once
  - peer B: `pull()` → record has `blob_ref`, no local file
  - peer B: `get_file("smith2024")` → downloads, verifies, returns cache path
  - peer A: `link_file("smith2024", same content)` → no re-upload (HEAD → 200)
  - peer C: `prefetch_blobs(["smith2024"])` → `fetched=1`
  - peer B: `prefetch_blobs()` → `already_cached=1, fetched=0`
  - peer A: `unlink_file("smith2024")` → blob untouched on remote
  - peer B: `pull()` → `blob_ref` cleared via LWW
  - corrupt cache → `get_file` re-fetches, surfaces mismatch error
  - LWW conflict: two peers link different files → newer `timestamp_hlc` wins
  - `@pytest.mark.integration`; skipped by default

## risks

1. **Large file handling**: boto3 single-part upload stalls above 5 GB. Mitigation:
   document limitation; multipart deferred. Academic PDFs (< 100 MB) unaffected.

2. **Network interruption during upload**: partial blob written to S3. Mitigation:
   `upload()` retry in adapter; idempotent via HEAD check on retry.

3. **Cache corruption**: local cache file manually modified. Mitigation: sha256 verify
   on every `get_file()`; discard and re-download.

4. **LWW blob conflict**: two peers link different files; older blob orphaned. Mitigation:
   document expected behavior; orphan is retrievable if needed.

5. **`.meta` staleness**: sidecar reflects the caller's citekey at upload time; another
   peer may have renamed the citekey before the next link. Mitigation: `.meta` is
   advisory only — validation never reads it.

6. **Storage cost accumulation**: orphaned blobs and unlinked files accumulate. Mitigation:
   document S3 lifecycle policy guidance in README; operator responsibility.
