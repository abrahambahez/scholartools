# spec: 008-distributed-sync-phase1

## objective

Implement the distributed sync layer: a composite storage adapter that manages
peer-to-peer reference synchronization via an S3-compatible backend, supporting
append-only change logs, HLC timestamps for causality, LWW conflict resolution,
soft-delete, snapshots for bootstrap, and a conflict store for user resolution.

Agents gain `push()`, `pull()`, `create_snapshot()`, `list_conflicts()`,
`resolve_conflict()`, and `restore_reference()`. Success: two peers can exchange
references without data loss, with deterministic conflict behavior, and full
auditability of all mutations.

Prerequisites: feat 006 (`passes: true`), feat 007 (`passes: true`).

## acceptance criteria

- WHEN an agent calls `push()` THEN the system collects all local `ChangeLogEntry`
  records newer than the last pushed HLC fence, signs each with the local device
  keypair, uploads them as `changes/{peer_id}/{hlc_timestamp}.json` to the remote
  backend, updates `sync_state.json`, and returns `PushResult` — never raises.
- WHEN an agent calls `pull()` THEN the system lists remote entries newer than the
  last pull fence, downloads and verifies each signature against the peer directory,
  replays verified entries in HLC order with LWW per-field, and returns `PullResult`
  with applied/rejected/conflicted counts — never raises.
- WHEN pull encounters two modifications to the same field within 60 s of each other
  (both HLC timestamps) THEN the system writes a `ConflictRecord` to `conflicts/` and
  preserves the local value.
- WHEN pull encounters a `delete_reference` entry and the local record has a local edit
  newer than the deletion timestamp THEN the system writes a conflict record and
  preserves the local record.
- WHEN a signature verification fails on a remote entry THEN the system writes the
  entry to `rejected/{hlc}-{peer_id}-{device_id}.json` and skips replay.
- WHEN an agent calls `list_conflicts()` THEN the system returns all `ConflictRecord`
  files from `conflicts/` — never raises.
- WHEN an agent calls `resolve_conflict(uid, field, winning_value)` THEN the system
  writes a new authoritative `update_reference` entry (fresh HLC, signed), uploads it,
  deletes the `ConflictRecord`, and returns `Result` — never raises.
- WHEN an agent calls `create_snapshot()` THEN the system serializes the full library
  plus `fence_hlc` (highest HLC in change log) and uploads to
  `snapshots/{iso_timestamp}.json` — never raises.
- WHEN a new peer bootstraps with no local library THEN it downloads the latest
  snapshot, uses its `fence_hlc` as the pull fence, pulls all entries with
  `timestamp_hlc >= fence_hlc`, and arrives at the same library state as the source
  peer (idempotent under LWW).
- WHEN `config.json` has no `sync` block THEN the system uses `LocalJsonAdapter`
  unchanged. WHEN a `sync` block is present THEN the system instantiates
  `SyncCompositeAdapter` with the configured S3 endpoint and credentials.
- WHEN two HLC calls occur within the same millisecond THEN the counter increments;
  on a new millisecond the counter resets to `0001`. Lexicographic ordering of
  `{iso_utc}-{counter:04d}-{peer_id}` guarantees causality.

## tasks

- [ ] task-01: `services/hlc.py` — HLC timestamp generation (blocks: none)
  - `now(peer_id: str) -> str` returning `{iso_utc}-{counter:04d}-{peer_id}`
  - per-process counter state; increment on same millisecond, reset on new millisecond
  - unit tests: same-ms increment, boundary reset, lexicographic ordering guarantee

- [ ] task-02: sync models in `models.py` (blocks: none)
  - `ChangeLogEntry`: op, uid, uid_confidence, citekey, data, peer_id, device_id,
    timestamp_hlc, signature
  - `ConflictRecord`: uid, field, local_value, local_timestamp_hlc, remote_value,
    remote_timestamp_hlc, remote_peer_id
  - `PushResult`: entries_pushed, errors
  - `PullResult`: applied_count, rejected_count, conflicted_count, errors
  - `SyncConfig`: endpoint (optional), bucket, access_key, secret_key
  - unit tests: validation and serialization round-trips

- [ ] task-03: `adapters/s3_sync.py` — S3 adapter implementing `RemoteSyncPort` (blocks: none)
  - `upload(local_path, remote_key)`, `download(remote_key, local_path)`,
    `list_keys(prefix) -> list[str]`, `exists(remote_key) -> bool`
  - constructor accepts `SyncConfig`; omitting `endpoint` targets AWS S3
  - unit tests: mocked boto3 calls, upload/download/list/exists paths

- [ ] task-04: `adapters/conflicts_store.py` — conflict record store (blocks: task-02)
  - `write_conflict(data_dir, conflict)`, `read_conflicts(data_dir) -> list[ConflictRecord]`,
    `delete_conflict(data_dir, uid, field)`
  - files at `{data_dir}/conflicts/{uid}-{field}.json`; auto-create directory
  - unit tests: write, read, delete, missing-directory creation

- [ ] task-05: `services/sync.py` — push logic (blocks: task-01, task-02, task-03)
  - `push(ctx) -> PushResult`: collect entries newer than `fence_push_hlc` from local
    change log at `{data_dir}/change_log/`, sign via `services/peers`, upload as single
    file, update `sync_state.json`
  - manage `sync_state.json` with `fence_push_hlc` and `fence_pull_hlc`
  - unit tests: fence tracking, signing delegation, upload error isolation

- [ ] task-06: `services/sync.py` — pull logic (blocks: task-01, task-04, task-05)
  - `pull(ctx) -> PullResult`: list remote keys, download, verify, replay in HLC order
  - LWW: compare `timestamp_hlc` lexicographically per field; skip if local is newer
  - conflict: same field, both sides changed, HLC within 60 s → `write_conflict`, keep local
  - soft-delete + local edit conflict path
  - rejected → `{data_dir}/rejected/{hlc}-{peer_id}-{device_id}.json`
  - update `fence_pull_hlc` after replay
  - unit tests: HLC ordering, LWW per-field, 60 s window, conflict path, rejection path

- [ ] task-07: `services/sync.py` — snapshot logic (blocks: task-05)
  - `create_snapshot(ctx) -> None`: serialize library + `fence_hlc`, upload to
    `snapshots/{iso_timestamp}.json`
  - unit tests: serialization, fence extraction, upload call

- [ ] task-08: `adapters/sync_composite.py` — `SyncCompositeAdapter` (blocks: task-03, task-05, task-06, task-07)
  - implements `StoragePort`; wraps `LocalJsonAdapter` + `RemoteSyncPort`
  - reads delegate to local; writes delegate to local and append `ChangeLogEntry` to
    `{data_dir}/change_log/{hlc_timestamp}.json`
  - upload happens only on explicit `push()` — no implicit remote writes
  - unit tests: read/write delegation, change log entry creation, no upload on write

- [ ] task-09: wire sync config into `Settings` and `ctx` init (blocks: task-02, task-03, task-08)
  - `config.py`: parse optional `sync` block from `config.json` into `SyncConfig`
  - `ctx` init: instantiate `SyncCompositeAdapter` if `SyncConfig` present, else
    `LocalJsonAdapter`
  - unit tests: config loading, adapter selection

- [ ] task-10: public API sync wrappers in `__init__.py` (blocks: task-08, task-09)
  - `push()`, `pull()`, `create_snapshot()`, `list_conflicts()`, `resolve_conflict()`,
    `restore_reference()` — all sync wrappers via `asyncio.run()`
  - `resolve_conflict`: write entry + sign + upload + delete conflict record
  - `restore_reference`: create `restore_reference` entry; push on next `push()` call
  - unit tests: all wrappers with mock ctx

- [ ] task-11: integration tests (blocks: task-10)
  - two peers with local adapters sharing a mock S3 backend
  - peer A pushes 3 refs → peer B pulls → libraries equal
  - concurrent field edit within 60 s → conflict detected
  - snapshot → new peer bootstraps → arrives at same state
  - soft-delete + local edit conflict path
  - `resolve_conflict` end-to-end: entry uploaded, conflict deleted
  - `@pytest.mark.integration`; skipped by default

## risks

1. **Clock skew**: HLC handles it, but the 60 s window may misalign with user intent
   under heavy skew. Document as a configurable parameter for future iterations.
2. **Snapshot consistency**: if change log grows during snapshot creation, new peers
   must pull entries after `fence_hlc`. LWW idempotency guarantees correctness.
3. **Concurrent push from same peer**: HLC includes `peer_id` not `device_id`, so two
   devices under the same peer may produce colliding HLC keys. Single-device-per-peer
   assumption must be documented; multi-device push requires `device_id` in HLC.
4. **boto3 weight**: optional import — only load if `SyncConfig` is present in config.
5. **S3 cost accumulation**: append-only log + multiple snapshots grow indefinitely.
   Document lifecycle policy recommendation in README.
