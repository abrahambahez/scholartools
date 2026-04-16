# feat 009: blob sync — content-addressed file distribution over S3

version: 0.1
status: deprecated

> **Deprecated (v0.13.0, spec 027):** Blob sync was removed from core to enforce the portability invariant. The S3/minio dependency does not belong in the core package. All blob distribution infrastructure will be re-introduced as part of a future `loretools-sync` plugin. This document is preserved as the design reference for that future work.
>
> **Local file operations** (`attach_file`, `detach_file`, `get_file`, `move_file`, `list_files`, `reindex_files`) remain implemented in core. Only the S3-upload layer (`sync_file`, `unsync_file`, `prefetch_blobs`, `upload_blobs`) is deprecated.

---

## context

Phase 1 (feat 008) syncs reference metadata only — PDFs and other linked files remain
local. This feat adds the blob layer: lazy on-demand file distribution using
content-addressed storage over the same S3-compatible backend.

Prerequisites: feat 008 (deprecated).

## proposed design

### storage layout

```
{shared-root}/
    blobs/{sha256}        ← raw file, key is its hex sha256
    blobs/{sha256}.meta   ← small JSON sidecar
```

### `sync_file(citekey) → Result` (proposed)

1. Hash local file → `sha256`
2. HEAD check — skip upload if already present
3. Upload to `blobs/{sha256}`
4. Write `.meta` sidecar
5. Write `link_file` change log entry
6. Set `blob_ref` on reference record

### `unsync_file(citekey) → Result` (proposed)

1. Write `unlink_file` change log entry
2. Clear `blob_ref`
3. Leave local file intact (remote blob is never deleted — append-only)

### `get_file` with S3 fallback (proposed)

When `blob_ref` is set and no local file exists:
1. Download from `blobs/{sha256}`
2. Verify sha256
3. Cache as `{blob_cache_dir}/{sha256}{ext}`
4. Return cache path

### `prefetch_blobs(citekeys) → PrefetchResult` (proposed)

Pre-download all referenced blobs for offline use.

### `upload_blobs() → UploadBlobsResult` (proposed)

Bulk-upload all locally attached files that lack `blob_ref`. Migration helper for
users who attached files before enabling sync.

## design decisions

**Lazy by default.** `pull_changelog()` never fetches blob content. Blobs arrive only
when `get_file` is called or `prefetch_blobs` is called explicitly.

**Content-addressed, not path-addressed.** Two peers uploading the same PDF produce the
same key. No dedup logic needed — HEAD check before upload is sufficient.

**Append-only blob storage.** Blobs are never deleted from remote. Storage cleanup is
operator responsibility via S3 lifecycle policies.

**No blob signing.** Blob content is verified implicitly via sha256. The `link_file`
change log entry is signed and carries the expected sha256.
