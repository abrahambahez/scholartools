# feat 021: file management refactor — explicit local/sync layers

version: 0.2
status: partially implemented

> **Updated (v0.13.0, spec 027):** The local file operations (`attach_file`, `detach_file`, `get_file`, `move_file`, `list_files`, `reindex_files`) are implemented in core. The S3 sync layer (`sync_file`, `unsync_file`, `prefetch_blobs`, `upload_blobs`) was removed from core in v0.13.0 to enforce the portability invariant — `minio` does not belong in the core package. The sync layer will be re-introduced as a future `loretools-sync` plugin.

---

## context

feat 009 (blob-sync) shipped `link_file` / `unlink_file` as combined operations that
always attempted both local copy and S3 upload in a single call. This created three
problems:

1. Local-only users had to handle S3 error paths that could never fire.
2. The operation was not reversible in stages.
3. `FileRecord.path` stored absolute paths, so moving the library directory broke all
   file records.

## implemented: local file layer

The local file lifecycle is fully implemented in `services/files.py`:

```
attach_file  →  copy to files/, filename-only path registered in _file
detach_file  →  delete local file, clear _file
get_file     →  return local files/ path (or None if not attached)
move_file    →  rename within files/, update _file.path
list_files   →  paginated FileRow list, sorted by citekey
reindex_files→  repair stale paths after library folder move
```

### `FileRecord.path` — filename only

`path` stores only the filename (`graeber2017.pdf`), never a full path. The files
directory is always `{library_dir}/files/`. This allows the library to be relocated
without invalidating file records.

### `attach_file(citekey, path) -> AttachResult`

1. Detect MIME type
2. Copy source file into `{files_dir}/{citekey}{ext}` (original untouched)
3. Write `FileRecord` with filename only
4. Update reference record

### `detach_file(citekey) -> DetachResult`

1. Delete file from `files/`
2. Clear `_file` on reference

### `get_file(citekey) -> Path | None`

Returns the local `files/` path if the file exists; `None` otherwise. No S3 fallback.

### `reindex_files() -> ReindexResult`

Repairs legacy absolute paths from pre-0.11.0 records to filename-only format.

```python
class ReindexResult(BaseModel):
    repaired: int
    already_ok: int
    not_found: int
```

## CLI commands (implemented)

| Command | API function |
|---|---|
| `scht files attach <citekey> <path>` | `attach_file` |
| `scht files detach <citekey>` | `detach_file` |
| `scht files get <citekey>` | `get_file` |
| `scht files move <citekey> <dest>` | `move_file` |
| `scht files list [--page N]` | `list_files` |
| `scht files reindex` | `reindex_files` |

## proposed: S3 sync layer (future `loretools-sync` plugin)

> **status: proposed** — The following operations were implemented in v0.11.0 and removed in v0.13.0. They belong in a `loretools-sync` plugin that imports `minio`.

The intended layered lifecycle was:

```
attach_file  →  local copy to files/, filename-only path registered
    ↓                (optional, sync users only)
sync_file    →  sha256 hash → HEAD check → S3 upload → blob_ref set
    ↓
unsync_file  →  blob_ref cleared, unlink_file change log entry written
    ↓
detach_file  →  local file deleted, _file cleared
```

### `sync_file(citekey) -> Result` (proposed)

1. Compute sha256 (streaming)
2. HEAD check — skip upload if already present in bucket
3. Upload to `blobs/{sha256}`
4. Write `.meta` sidecar
5. Write `link_file` change log entry
6. Set `blob_ref` on reference record

S3 failure is transactional — `blob_ref` is not set if upload fails.

### `unsync_file(citekey) -> Result` (proposed)

1. Write `unlink_file` change log entry
2. Clear `blob_ref`
3. Leave local file intact (remote blob is never deleted — append-only storage)

### `upload_blobs() -> UploadBlobsResult` (proposed)

Bulk-upload all locally attached files that lack `blob_ref`. Migration helper.

### `prefetch_blobs(citekeys) -> PrefetchResult` (proposed)

Pre-download all referenced blobs for offline use.

## design decisions (locked for local layer)

- **`files_dir` is not configurable** — always `library_dir/files`. Eliminates path confusion bugs.
- **`attach_file` never deletes the source** — callers control their originals.
- **Filename-only `FileRecord.path`** — enables library relocation without data loss.
- **`reindex_files` for migration** — repairs pre-0.11.0 absolute-path records without a hard migration.
