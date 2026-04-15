# spec: 023-upload-blobs-command

## objective

Add `scht sync upload-blobs` — a bulk blob upload command for initial migration.
Uploads all locally-attached files to S3, sets `blob_ref` on each record, and writes
`library.json` once. Writes zero change log entries; callers must follow with
`scht sync snapshot` to publish the state.

## context

`scht sync sync-file` writes one change log entry per file. On a library with hundreds
of records this produces hundreds of small JSON files in `change_log/`, degrading
filesystem performance and making no semantic sense (a bulk initial upload is one
operation, not N). The snapshot already captures `blob_ref` state, so change log
entries add no value for this use case.

## acceptance criteria

- WHEN `upload-blobs` is called and a record has `_file` but no `blob_ref` THEN the
  blob is uploaded to `blobs/<sha256>` and `blob_ref` is set on the record
- WHEN `upload-blobs` is called and a record already has a `blob_ref` matching the
  local file's sha256 THEN the record is skipped (no re-upload, no re-write)
- WHEN `upload-blobs` is called and the blob already exists in S3 THEN the upload is
  skipped but `blob_ref` is still set on the record if missing
- WHEN `upload-blobs` completes THEN `library.json` is written exactly once regardless
  of how many records were processed
- WHEN `upload-blobs` completes THEN zero change log entries have been written
- WHEN `upload-blobs` completes THEN the result reports counts:
  `uploaded`, `skipped`, `failed`
- WHEN a record has no `_file` THEN it is ignored silently
- WHEN a file cannot be read or hashed THEN that record is counted as `failed`, the
  error is recorded, and processing continues for remaining records
- WHEN `sync` is not configured THEN the command exits with an error immediately
- WHEN called with `--plain` THEN output is human-readable: one line per count

## tasks

- [ ] task-01: `services/sync.py` — add `upload_blobs(ctx)` (blocks: none)
  - Iterate all records; skip records without `_file`
  - Skip records where `blob_ref` already matches `sha256:<computed>`
  - Upload blob if not already in S3 (`s3_sync.exists` check)
  - Upload `.meta` sidecar (same format as `sync_file`)
  - Collect results into `uploaded / skipped / failed` counts
  - Write `library.json` once after all records processed
  - Return a new `UploadBlobsResult` model

- [ ] task-02: `models.py` — add `UploadBlobsResult` (blocks: none)
  - Fields: `uploaded: int`, `skipped: int`, `failed: int`,
    `errors: list[str]`

- [ ] task-03: `__init__.py` — expose `upload_blobs()` sync wrapper (blocks: task-01, task-02)

- [ ] task-04: `cli/sync.py` — add `upload-blobs` subcommand (blocks: task-03)
  - Call `scholartools.upload_blobs()`
  - `--plain` prints `uploaded: N  skipped: N  failed: N`
  - JSON output via `exit_result`

- [ ] task-05: `docs/remote-setup.md` — update migration sections (blocks: task-04)
  - Replace `scht sync sync-file <citekey>  # repeat for each` in the manual
    migration section with `scht sync upload-blobs`
  - Add a note that `upload-blobs` must be followed by `scht sync snapshot`

- [ ] task-06: unit tests (blocks: task-01, task-02)
  - Mock S3 and file I/O; assert `library.json` written once
  - Test skip logic: blob_ref already set and matching sha256
  - Test S3-exists skip: blob not re-uploaded but blob_ref still set
  - Test failed record: unreadable file counted in `failed`, others proceed
  - Test no-sync-config path returns error immediately
