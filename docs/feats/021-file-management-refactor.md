# feat 021: file management refactor — explicit local/sync layers

version: 0.1
status: current

## context

feat 009 (blob-sync) shipped `link_file` / `unlink_file` as combined operations that
always attempted both local copy and S3 upload in a single call. This created three
problems:

1. Local-only users had to handle S3 error paths that could never fire.
2. The operation was not reversible in stages — you could not "attach a file locally now,
   sync it to S3 later."
3. `FileRecord.path` stored absolute paths, so moving the library directory broke all
   file records.

## design

Split the file lifecycle into two explicit, independent layers:

```
attach_file  →  local copy to files/, filename-only path registered
    ↓                (optional, sync users only)
sync_file    →  sha256 hash → HEAD check → S3 upload → blob_ref set
    ↓
unsync_file  →  blob_ref cleared, unlink_file change log entry written
    ↓
detach_file  →  local file deleted, _file cleared (blocked if blob_ref set)
```

Local users only ever call `attach_file` / `detach_file`. Sync users stack
`sync_file` / `unsync_file` on top. The discriminator is `ctx.sync_config` — no flags.

## what changes

### `FileRecord.path` — filename only

`path` now stores only the filename (`graeber2017.pdf`), never a full path. The files
directory is always `{library_dir}/files/` (computed, not configurable). This allows the
library to be relocated without invalidating file records.

### `attach_file(citekey, path) → Result`

1. Detect MIME type
2. Copy source file into `{files_dir}/{citekey}{ext}`
3. Write `FileRecord` with filename only
4. Update reference record

No S3 side effects. Works for local-only users.

### `detach_file(citekey) → Result`

1. Block if `blob_ref` is set — caller must `unsync_file` first
2. Delete file from `files/`
3. Clear `_file` on reference

### `sync_file(citekey) → Result`

Requires `sync` block in config.

1. Compute sha256 (streaming)
2. HEAD check — skip upload if already present in bucket
3. Upload to `blobs/{sha256}` 
4. Write `.meta` sidecar (`blobs/{sha256}.meta`)
5. Write `link_file` change log entry
6. Set `blob_ref` on reference record

S3 failure is transactional — if upload fails, `blob_ref` is not set and the record
is unchanged.

### `unsync_file(citekey) → Result`

1. Write `unlink_file` change log entry
2. Clear `blob_ref`
3. Leave local file intact

Remote blob is never deleted (append-only storage).

### `reindex_files() → ReindexResult`

Repairs legacy absolute paths from pre-0.11.0 records. For each record with a `_file`
whose path looks like an absolute path, extracts the filename part and overwrites. Records
where the computed `files/{filename}` does not exist are counted as `not_found`.

```python
class ReindexResult(BaseModel):
    repaired: int
    already_ok: int
    not_found: int
```

### `get_file(citekey) → Path | None`

1. Load record
2. If no `_file` and no `blob_ref` → return None
3. If `_file.path` exists locally → return path (resolves relative to `files_dir`)
4. If `blob_ref` and sync configured → download from S3, verify sha256, cache as
   `{blob_cache_dir}/{sha256}{ext}`, return path
5. If sha256 mismatch → return None (surfaces as implicit error)

### blob cache naming

Cache files are named `{sha256}{ext}` (e.g. `e3b0c44….pdf`). The extension is read from
the `.meta` sidecar at download time. Legacy no-extension cache files are evicted and
re-downloaded on next `get_file` access.

### `upload_blobs() → UploadBlobsResult`

Bulk convenience operation: finds all locally-attached references without `blob_ref` and
calls `sync_file` on each. Useful when files were attached locally before enabling sync.

```python
class UploadBlobsResult(BaseModel):
    uploaded: int
    skipped: int
    failed: int
    errors: list[str]
```

## public API changes

Removed (v0.11.0):
- `link_file(citekey, path)` — replaced by `attach_file` + `sync_file`
- `unlink_file(citekey)` — replaced by `unsync_file` + `detach_file`

Added:
- `attach_file(citekey, path) → Result`
- `detach_file(citekey) → Result`
- `sync_file(citekey) → Result`
- `unsync_file(citekey) → Result`
- `reindex_files() → ReindexResult`
- `upload_blobs() → UploadBlobsResult`

Unchanged:
- `get_file(citekey) → Path | None`
- `prefetch_blobs(citekeys) → PrefetchResult`
- `move_file(citekey, dest_name) → MoveResult`
- `list_files(page) → FilesListResult`

## CLI commands

| Command | API function |
|---|---|
| `scht files attach <citekey> <path>` | `attach_file` |
| `scht files detach <citekey>` | `detach_file` |
| `scht files reindex` | `reindex_files` |
| `scht sync sync-file <citekey>` | `sync_file` |
| `scht sync unsync-file <citekey>` | `unsync_file` |

## decisions

- **`detach_file` blocks on `blob_ref`** — callers must unsync first. No alias that does
  both: the two-step is intentional to prevent accidental loss of the remote pointer.
- **`files_dir` is not configurable** — always `library_dir/files`. Eliminates a class
  of path confusion bugs. Callers that previously passed `files_dir` now rely on the
  computed default.
- **S3 failure is transactional in `sync_file`** — `blob_ref` is set only after a
  confirmed upload. Partial failure (local copy ok, S3 fail) leaves `blob_ref=None`.
  Retry by calling `sync_file` again.
- **`upload_blobs` for migration** — allows users who attached files before enabling sync
  to bulk-promote without per-record calls.
