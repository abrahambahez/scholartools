# spec: 021-file-management-refactor

## findings

Discovered during a library folder migration. Three compounding bugs:

1. `FileRecord.path` stores absolute paths (`str(src.resolve())`). Moving `library_dir` silently breaks all `_file` references — `get_file` returns `None`. No repair path without re-running `link_file`.

2. `link_file` (public API → `sync_service.link_file`) conflates two separate concerns: local file management (copy + register) and S3 upload. These should be independently callable to support the local-first progressive enhancement model.

3. Blob cache files are named `{sha256}` (no extension). `get_file` returns these for sync users. `xdg-open {sha256}` fails — OS cannot determine the application. Agent "open file" use cases break.

Spec 011 (`local-file-progressive-enhancement`) addressed part of (2) but retained `link_file` semantics and did not fix (1) or (3). This spec supersedes spec 011.

Affected code:
- `services/sync.py`: `link_file` (396), `unlink_file` (493), `get_file` (539), `prefetch_blobs` (581)
- `services/files.py`: `link_file` (24), `move_file` (58), `list_files` (75)
- `services/blobs.py`: `blob_cache_path`
- `models.py`: `FileRecord.path` (32)
- `__init__.py`: all file-related public exports

## objective

Replace `link_file`/`unlink_file` with four explicit functions across two independent layers:

```
local:  attach_file  ←→  detach_file
sync:    sync_file   ←→  unsync_file
```

Fix `FileRecord.path` to store only the filename so libraries survive folder moves. Add `reindex_files()` as a repair command. Fix blob cache filenames to include the original extension.

## acceptance criteria

### relative paths

`files_dir` is always `library_dir / "files"` — computed, not configurable. Moving the library = update `library_dir` in `config.json`.

- WHEN any operation writes `_file` THEN `FileRecord.path` MUST store only the filename (e.g. `graeber2017.pdf`), never a full path
- WHEN `get_file` or `list_files` reads `FileRecord.path` THEN it MUST resolve as `files_dir / filename`
- WHEN `get_file` reads a legacy absolute path AND the file exists at that path THEN it MUST return it unchanged
- WHEN `get_file` reads a legacy absolute path AND the file is missing THEN it MUST attempt `files_dir / Path(legacy).name` as fallback
- WHEN any file operation receives a path outside `files_dir` (after copy) THEN it MUST return `Result(ok=False)`

### `attach_file`

- WHEN `attach_file(citekey, path)` is called AND `path` is outside `files_dir` THEN the file MUST be copied to `files_dir/{citekey}{ext}` before registering
- WHEN `attach_file(citekey, path)` is called AND `path` is already inside `files_dir` THEN no copy MUST occur
- WHEN `attach_file(citekey, path)` completes successfully THEN `_file` MUST be set with the filename only and `Result(ok=True)` returned
- WHEN `attach_file` is called AND `path` does not exist on disk THEN it MUST return `Result(ok=False)`
- WHEN `attach_file` is called THEN no S3 call MUST occur and no change log entry MUST be written regardless of `sync_config`

### `detach_file`

- WHEN `detach_file(citekey)` is called AND `blob_ref` is set on the record THEN it MUST return `Result(ok=False, error="file is synced — call unsync_file first")`
- WHEN `detach_file(citekey)` is called AND `blob_ref` is absent THEN the file MUST be deleted from `files_dir` (ENOENT ignored), `_file` MUST be cleared, and `Result(ok=True)` returned
- WHEN `detach_file` is called THEN no S3 call MUST occur and no change log entry MUST be written

### `sync_file`

- WHEN `sync_file(citekey)` is called AND `_file` is not set THEN it MUST return `Result(ok=False, error="no file attached — call attach_file first")`
- WHEN `sync_file(citekey)` is called AND `ctx.sync_config is None` THEN it MUST return `Result(ok=False, error="sync not configured")`
- WHEN `sync_file(citekey)` is called AND `_file` is set AND sync is configured THEN it MUST: compute sha256 of the file in `files_dir`, conditionally upload blob to S3, write `link_file` change log entry, set `blob_ref` on the record
- WHEN `sync_file` S3 upload fails THEN `blob_ref` MUST NOT be set and the error MUST be surfaced in `Result`

### `unsync_file`

- WHEN `unsync_file(citekey)` is called AND `blob_ref` is absent THEN it MUST return `Result(ok=False, error="file is not synced")`
- WHEN `unsync_file(citekey)` is called AND `blob_ref` is set THEN it MUST clear `blob_ref`, write `unlink_file` change log entry, and return `Result(ok=True)`
- WHEN `unsync_file` completes THEN `_file` and the local file on disk MUST remain untouched

### `reindex_files`

- WHEN `reindex_files()` is called THEN it MUST scan `files_dir` for all files, build a `{stem: filename}` map
- WHEN a record has `_file` set AND `files_dir / _file.path` does not exist AND the stem matches a file in `files_dir` THEN `_file.path` MUST be updated to the matched filename
- WHEN `reindex_files()` completes THEN it MUST return `ReindexResult(repaired, already_ok, not_found)`

### blob cache extension

- WHEN a blob is downloaded from S3 THEN the `.meta` sidecar MUST be fetched, the original filename extension extracted, and the cache file written as `{sha256}{ext}`
- WHEN `get_file` returns a blob cache path THEN the path MUST include the original extension
- WHEN a legacy cache file `{sha256}` (no extension) exists THEN on next `get_file` it MUST be deleted and re-downloaded with the correct extension

### removal of old API

- `link_file` and `unlink_file` MUST be removed from `__init__.py`, `services/sync.py`, `services/files.py`, and all tests — no aliases, no stubs

## tasks

- [x] task-01: `services/blobs.py` — add `ext` param to `blob_cache_path` — blocks: none
  - `blob_cache_path(data_dir, sha256, ext="") -> Path`
  - All existing call sites pass `ext=""` (default) — no breakage during transition

- [x] task-02: `services/sync.py` — fix blob cache extension in `get_file` and `prefetch_blobs` — blocks: task-01
  - On download: fetch `.meta` sidecar, extract extension from `filename` field, pass to `blob_cache_path`
  - On cache hit check: look for `{sha256}{ext}` first; if legacy `{sha256}` exists, delete and re-download
  - Unit tests: cached file has extension; legacy no-ext file is evicted and replaced

- [x] task-03: `services/files.py` — add `_resolve_file_path` helper, fix `move_file` and `list_files` — blocks: none
  - `_resolve_file_path(ctx, raw_path) -> Path`: relative → `files_dir / raw_path`; absolute + exists → as-is; absolute + missing → `files_dir / Path(raw_path).name`
  - `move_file`: store updated path as filename only
  - `list_files`: resolve via `_resolve_file_path` before returning `FileRow`
  - Unit tests: relative resolves; legacy absolute resolves; legacy missing falls back

- [x] task-04: `services/sync.py` — implement `attach_file` — blocks: task-03
  - `async def attach_file(ctx, citekey, path) -> Result`
  - If path is outside `files_dir`: copy to `files_dir/{citekey}{ext}`
  - If path is inside `files_dir`: no copy
  - Store filename only in `_file`; no S3, no change log
  - Unit tests: outside path copies and registers; inside path registers only; missing path errors; `blob_ref` untouched

- [x] task-05: `services/sync.py` — implement `detach_file` — blocks: task-04
  - `async def detach_file(ctx, citekey) -> Result`
  - Error if `blob_ref` set
  - Delete file from `files_dir` (ENOENT ignored), clear `_file`
  - Unit tests: synced record errors; local-only record deletes and clears; missing file on disk is ok

- [x] task-06: `services/sync.py` — implement `sync_file` — blocks: task-04
  - `async def sync_file(ctx, citekey) -> Result`
  - Error if `_file` not set; error if `sync_config` is None
  - Hash file at `files_dir / _file.path`, conditional S3 upload, change log entry, set `blob_ref`
  - S3 failure must not set `blob_ref`
  - Unit tests: no `_file` errors; no sync config errors; happy path sets `blob_ref`; S3 failure leaves record clean

- [x] task-07: `services/sync.py` — implement `unsync_file` — blocks: task-06
  - `async def unsync_file(ctx, citekey) -> Result`
  - Error if `blob_ref` absent
  - Clear `blob_ref`, write `unlink_file` change log entry; leave `_file` and disk file intact
  - Unit tests: not synced errors; happy path clears `blob_ref` only; `_file` preserved

- [x] task-08: `services/files.py` — implement `reindex_files` — blocks: task-03
  - `async def reindex_files(ctx) -> ReindexResult`
  - Scan `files_dir` glob `*.*`, build `{stem: filename}` map
  - For each record with `_file`: resolve path; if missing but stem in map, update to matched filename
  - Add `ReindexResult(repaired, already_ok, not_found)` to `models.py`
  - Unit tests: stale path repaired; already-ok left alone; no match counted as not_found

- [x] task-09: `__init__.py` — wire public API — blocks: task-08
  - Add: `attach_file`, `detach_file`, `sync_file`, `unsync_file`, `reindex_files`
  - Remove: `link_file`, `unlink_file` from all public exports and service modules

- [x] task-10: CLI — blocks: task-09
  - `cli/files.py`: replace `_link`/`link` with `_attach`/`attach` (citekey, path); replace `_unlink`/`unlink` with `_detach`/`detach` (citekey); add `_reindex`/`reindex` (no args)
  - `cli/sync.py`: add `_sync_file`/`sync-file` (citekey) and `_unsync_file`/`unsync-file` (citekey)
  - Keep `get`, `move`, `list`, `prefetch` unchanged

- [x] task-11: integration tests — blocks: task-10
  - `tests/integration/test_file_management.py`
  - Local workflow: `attach_file` → `get_file` → `detach_file`
  - Sync workflow: `attach_file` → `sync_file` → `get_file` returns `.pdf` path → `unsync_file` → `detach_file`
  - Guard violations: `sync_file` without attach errors; `detach_file` while synced errors
  - Repair workflow: stale `_file.path` → `reindex_files` → `get_file` resolves
  - `@pytest.mark.integration`

- [x] task-12: full suite green — blocks: task-11
  - `uv run pytest` — no regressions
  - `uv run ruff check .` — zero new errors

## risks

1. **Legacy `_file.path` absolute paths.** The fallback in `_resolve_file_path` is safe because files were always inside `files_dir` — the filename is the stable identity. `reindex_files` is the authoritative repair; document that users run it after updating `library_dir`.

2. **`detach_file` blocking on `blob_ref`.** Callers must explicitly `unsync_file` first. This is intentional — prevents orphaned remote blob references. No aliases needed since there are no production users.

3. **`sync_file` S3 partial failure.** Local file and `_file` intact; `blob_ref` not set. Retry `sync_file` to recover. Document in API.

4. **Blob cache eviction.** Legacy no-extension cache files are deleted on next `get_file`. One extra S3 download per affected file. No data loss.
