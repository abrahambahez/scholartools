# spec: 011-local-file-progressive-enhancement

## findings

`link_file` in `services/sync.py` (lines 375–447) unconditionally routes through the sync path. When `ctx.sync_config is None`, it computes a sha256 hash and sets `blob_ref` on the record but **never copies the file to `files_dir`** and never sets `file_record`. The file is unreachable — `get_file()` always returns `None` because `blob_ref` requires S3 access, and `move_file()` / `list_files()` operate on `files_dir` which is always empty.

Root cause: feat 009 replaced the `files_service` routing in the public API with `sync_service` routing for `link_file`, `unlink_file`, `get_file`. The local behavior was not preserved as a base layer.

`move_file` and `list_files` route through `files_service` — their behavior is consistent but vacuous for local users because nothing ever lands in `files_dir`.

Affected public API lines: `__init__.py` 230–242.
Affected service: `services/sync.py` `link_file` (375), `unlink_file` (450), `get_file` (490).

## objective

Restore the local-first guarantee by implementing progressive enhancement: local file management (copy to `files_dir`, set `file_record`) is the base that always runs; S3 blob distribution stacks on top when `ctx.sync_config is not None`. No new config fields, no routing flags. The presence of `ctx.sync_config` is the sole discriminator.

## acceptance criteria

- WHEN `link_file(citekey, path)` is called and `ctx.sync_config is None` THEN the file MUST be copied to `{files_dir}/{citekey}{ext}`, `file_record` MUST be set on the record (path, mime_type, size_bytes, added_at), and the function MUST return `Result(ok=True)` without computing any hash or making any S3 call.

- WHEN `link_file(citekey, path)` is called and `ctx.sync_config is not None` THEN the function MUST execute all steps in sequence: (1) copy file to `files_dir` and set `file_record`, (2) compute sha256, conditionally upload to S3, set `blob_ref`, write change log entry, and return `Result(ok=True)`.

- WHEN `unlink_file(citekey)` is called THEN the file MUST be deleted from `files_dir` (ENOENT ignored) and `file_record` MUST be cleared from the record; if `ctx.sync_config is not None` THEN `blob_ref` MUST also be cleared and a change log entry written.

- WHEN `get_file(citekey)` is called and `ctx.sync_config is not None` THEN the existing blob-cache / S3-download path MUST be used (unchanged).

- WHEN `get_file(citekey)` is called and `ctx.sync_config is None` THEN the function MUST read `file_record.path` from the record and return it as a `Path` if the file exists on disk, else `None`.

- WHEN `list_files()` is called with no `sync_config` THEN it MUST return all records whose `file_record` is set, with correct path, mime_type, size_bytes.

- WHEN `move_file()` is called THEN it MUST update `file_record.path` without touching `blob_ref` or any other field.

- WHEN a local-only user later adds `sync_config` and calls `link_file()` on a previously linked citekey THEN the function MUST overwrite the local copy, set `blob_ref`, write the change log entry, and leave the record in a consistent state.

## tasks

- [ ] task-01: `services/sync.py` — refactor `link_file` — blocks: none
  - Add private `_copy_to_files_dir(ctx, citekey, src: Path) -> FileRecord` that copies the file and returns a populated `FileRecord`
  - Refactor `link_file`: call `_copy_to_files_dir` unconditionally first; then, if `ctx.sync_config is not None`, run existing hash/upload/blob_ref/change-log logic
  - Unit tests: local-only path copies file and sets `file_record`; sync path runs both steps; S3 failure does not corrupt `file_record`

- [ ] task-02: `services/sync.py` — refactor `unlink_file` — blocks: task-01
  - Add private `_delete_from_files_dir(ctx, citekey)` that deletes the file (ENOENT ignored) and clears `file_record`
  - Refactor `unlink_file`: call `_delete_from_files_dir` unconditionally; then, if `ctx.sync_config is not None`, clear `blob_ref` and write change log entry (existing logic)
  - Unit tests: local-only clears file and `file_record`; sync path also clears `blob_ref` and writes log

- [ ] task-03: `services/sync.py` — refactor `get_file` — blocks: task-01
  - Preserve existing S3/blob-cache path when `ctx.sync_config is not None` and `blob_ref` present
  - Add fallback: if sync absent or `blob_ref` absent, read `file_record` from record dict, return `Path(file_record["path"])` if it exists on disk, else `None`
  - Unit tests: sync path unchanged; local fallback returns correct path; missing file returns None

- [ ] task-04: `services/files.py` — verify interoperability — blocks: task-03
  - Confirm `move_file` updates only `file_record.path`; leaves `blob_ref` intact
  - Confirm `list_files` reads from `file_record`; no change needed if already correct
  - Unit tests: `move_file` on local-linked file works; `list_files` returns entries with no sync_config

- [ ] task-05: `tests/unit/test_file_local_progressive.py` — blocks: task-04
  - `test_link_file_local_only` — no sync_config: file copied, `file_record` set, `blob_ref` absent
  - `test_unlink_file_local_only` — no sync_config: file deleted, `file_record` cleared
  - `test_get_file_local_only` — no sync_config: returns local path
  - `test_get_file_local_missing` — file deleted from disk: returns None
  - `test_list_files_local_only` — no sync_config: returns local entries
  - `test_move_file_preserves_blob_ref` — move on synced file leaves `blob_ref` intact

- [ ] task-06: `tests/integration/test_file_progressive_enhancement.py` — blocks: task-05
  - Local-only workflow: link → get → move → list → unlink, all without sync_config
  - Sync workflow: link → verify file_record AND blob_ref both set → get returns S3 path (mocked)
  - Mixed state: local-linked record, add sync_config, re-link → both fields populated
  - `@pytest.mark.integration`

- [ ] task-07: full suite green — blocks: task-06
  - `uv run pytest` — no regressions on existing blob sync, peer sync, or file tests
  - `uv run ruff check .` — zero new errors

- [ ] task-08: `feature_list.json` — blocks: none
  - Append `{"id": "local-file-progressive-enhancement", "title": "Local-first file ops — progressive enhancement stacking blob sync on local copy", "spec": "specs/011-local-file-progressive-enhancement.md", "passes": false}`

## risks

1. **File copy overhead for S3 users.** `link_file` now always copies to `files_dir` even when sync is configured. For large PDFs this doubles disk I/O. Acceptable for the local-first model; document as expected behavior.

2. **Partial failure state.** If file copy succeeds but S3 upload fails, the record will have `file_record` but no `blob_ref`. Recoverable by retrying `link_file`. Document in API.

3. **No backfill for existing sync users.** Records that were linked with the old code have `blob_ref` but no `file_record`. `get_file` falls back to S3 for these — still works. `list_files` will not show them. Users must re-call `link_file` to populate `file_record`. Document in migration notes.
