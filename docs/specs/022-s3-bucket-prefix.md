# spec: 022-s3-bucket-prefix

## objective

Allow users to scope all S3 objects under a subdirectory by specifying
`bucket: "bucketname/subdir"` in `config.json`. The adapter splits on the first `/`
and prepends the prefix to every object key. No new model field, no config schema
change — purely an internal adapter change.

## acceptance criteria

- WHEN `SyncConfig.bucket` contains no slash THEN the adapter uses it as-is and
  prepends no prefix to any key
- WHEN `SyncConfig.bucket` is `"mybucket/scholartools"` THEN the adapter extracts
  bucket `"mybucket"` and prepends `"scholartools/"` to all object keys
- WHEN `SyncConfig.bucket` is `"mybucket/a/b"` THEN the adapter extracts bucket
  `"mybucket"` and prepends `"a/b/"` to all object keys
- WHEN `upload(config, path, "changes/peer/ts.json")` is called with prefix `"proj"` THEN
  minio receives `fput_object("mybucket", "proj/changes/peer/ts.json", ...)`
- WHEN `download(config, "blobs/sha256", path)` is called with prefix `"proj"` THEN
  minio receives `fget_object("mybucket", "proj/blobs/sha256", ...)`
- WHEN `list_keys(config, "changes/")` is called with prefix `"proj"` THEN
  minio receives `list_objects("mybucket", prefix="proj/changes/", ...)` AND returned
  keys have the config prefix stripped before being returned to the caller (e.g.
  `"proj/changes/peer/ts.json"` → `"changes/peer/ts.json"`)
- WHEN `exists(config, "snapshots/ts.json")` is called with prefix `"proj"` THEN
  minio receives `stat_object("mybucket", "proj/snapshots/ts.json", ...)`
- WHEN `upload_bytes(config, data, "blobs/sha256")` is called with prefix `"proj"` THEN
  minio receives `put_object("mybucket", "proj/blobs/sha256", ...)`
- WHEN `bucket: "mybucket"` (no slash) THEN existing behaviour is unchanged —
  no regression for current users

## tasks

- [x] task-01: `adapters/s3_sync.py` — add `_split(config)` helper (blocks: none)
  - Parse `config.bucket` on the first `/`
  - Return `(bucket_name: str, prefix: str)` where prefix ends with `/` if non-empty,
    empty string otherwise
  - Edge: `"mybucket/"` → `("mybucket", "")` (trailing slash → no prefix)

- [x] task-02: `adapters/s3_sync.py` — update all 5 operations (blocks: task-01)
  - `upload`, `download`, `exists`, `upload_bytes`: prepend prefix to `remote_key`
  - `list_keys`: prepend prefix to the `prefix` parameter; strip the config prefix
    from returned keys so callers always see unprefixed keys

- [x] task-03: `docs/remote-setup.md` — document `bucket` subdir syntax in Section 2 (blocks: task-01)

- [x] task-04: unit tests (blocks: task-02)
  - Test `_split()` directly: no-slash, single-segment, multi-segment, trailing-slash
  - Test each operation with mocked minio to assert key construction
  - Existing test cases must pass unchanged

## risks

- **Trailing slash edge case**: `"mybucket/"` could be a typo. Normalising it to no
  prefix is the safest default.
