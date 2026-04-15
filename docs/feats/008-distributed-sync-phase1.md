# 008: distributed sync phase 1 — append-only change log, push/pull, conflict resolution

## context

Full design is in `docs/rfc/001-distributed-sync.md`. Peer identity and pull
verification are covered by feat 007 and already implemented. uid generation and
deduplication are covered by feat 006 and already implemented.

This feat covers the sync layer itself: composite adapter, HLC timestamps, change log
format, push/pull protocol, LWW merge, conflict store, soft-delete, and snapshots.

**Backend scope:** S3-compatible only (AWS S3, Backblaze B2, MinIO). A single adapter
covers all three via endpoint override — no rsync adapter in v1. This keeps the port
interface minimal and the adapter surface to one implementation.

Prerequisites: feat 006 (`passes: true`), feat 007 (`passes: true`).

## what changes

### new port (`ports.py` or `models.py`)

```python
class RemoteSyncPort(Protocol):
    def upload(self, local_path: Path, remote_key: str) -> None: ...
    def download(self, remote_key: str, local_path: Path) -> None: ...
    def list_keys(self, prefix: str) -> list[str]: ...
    def exists(self, remote_key: str) -> bool: ...
```

### HLC timestamps (`services/hlc.py`)

New module. Implements Hybrid Logical Clock: `now(peer_id) -> str` returns a sortable
string `{iso_utc}-{counter:04d}-{peer_id}`. Counter increments on same-millisecond
events; reset to `0001` otherwise.

### change log models (`models.py`)

```python
class ChangeLogEntry(BaseModel):
    op: Literal["add_reference", "update_reference", "delete_reference", "restore_reference"]
    uid: str
    uid_confidence: Literal["authoritative", "semantic"]
    citekey: str
    data: dict | None = None        # full CSL-JSON for add; changed fields only for update
    peer_id: str
    device_id: str
    timestamp_hlc: str
    signature: str

class ConflictRecord(BaseModel):
    uid: str
    field: str
    local_value: Any
    local_timestamp_hlc: str
    remote_value: Any
    remote_timestamp_hlc: str
    remote_peer_id: str
```

### composite adapter (`adapters/sync_composite.py`)

New module. Implements `StoragePort`. Holds a `LocalJsonAdapter` (existing) and a
`RemoteSyncPort` instance. Services and the public API see only `StoragePort` — no
sync-specific logic leaks upward.

**push_changelog flow:**
1. Call `merge()` to commit any local staged work.
2. Collect all local `ChangeLogEntry` records not yet pushed (tracked by a local
   `sync_state.json` with the last pushed HLC fence).
3. Sign each entry using the local device keypair (delegates to `services/peers.py`).
4. Write all entries as a single JSON file to
   `changes/{peer_id}/{hlc_timestamp}.json` via `RemoteSyncPort.upload`.
5. Update `sync_state.json` with the new fence.

**pull_changelog flow:**
1. Load peer directory via `PeerDirectoryAdapter` (feat 007).
2. List `changes/` keys newer than the last known pull fence via `RemoteSyncPort.list_keys`.
3. Download and verify each entry (`verify_entry` from `services/peers.py`); write
   failures to `rejected/{hlc}-{peer_id}-{device_id}.json`.
4. Replay verified entries in HLC order against the local library (LWW: skip if local
   record has a newer HLC for the same field).
5. Detect conflicts: same field, both sides changed, HLC timestamps within 60 s →
   write `ConflictRecord` to `conflicts/` store; do not overwrite local record.
6. Update pull fence in `sync_state.json`.
7. Return a pull result with counts: applied, rejected, conflicted.

**LWW rule:** for `update_reference`, compare per-field. The entry with the greater
`timestamp_hlc` string (lexicographic) wins. Outside the 60 s window, LWW applies
silently. Within the window, a conflict record is written and the local value is
preserved until resolved.

**soft-delete / restore:** `delete_reference` sets `deleted: True` on the local record.
`restore_reference` clears it. Deleted records are excluded from all list/filter ops
unless `include_deleted=True`. Delete-vs-newer-local-edit: apply the delete, write the
local edit to `conflicts/` as a pending restore decision.

### snapshot service (`services/sync.py`)

`create_snapshot()`: writes the full current library state plus a `fence_hlc` field
(HLC of the most recent entry in the change log) to
`snapshots/{iso_timestamp}.json` via `RemoteSyncPort.upload`.

Bootstrap for new peers (documented in `pull()` return value and README):
1. Download latest snapshot; load its `fence_hlc`.
2. Pull all change log entries with `timestamp_hlc >= fence_hlc`.
3. Replay on top of snapshot (idempotent under LWW).

### sync config (`config.py` / `Settings`)

New optional `sync` field in `config.json`:

```json
{ "sync": { "endpoint": "https://minio.example.org", "bucket": "scholartools", "access_key": "...", "secret_key": "..." } }
```

Omitting `endpoint` targets AWS S3 (boto3 default). `SyncCompositeAdapter` is
instantiated only when a `sync` block is present; otherwise the local adapter is used
unchanged.

### S3 adapter (`adapters/s3_sync.py`)

Single adapter implementing `RemoteSyncPort` via `minio>=7.0.0`. Covers AWS S3, Backblaze B2,
and MinIO through endpoint override — no code changes per deployment, only config.
`minio` is an optional dependency in the `sync` extras group (`pip install scholartools[sync]`).

> **Changed in v0.9.1:** replaced `boto3`/`botocore` (~15 MB) with `minio` SDK (~500 KB) — same API surface, significantly lighter install.

### conflicts store (`adapters/conflicts_store.py`)

Plain functions to read/write/delete `ConflictRecord` files under `{data_dir}/conflicts/`.
One JSON file per conflict, named `{uid}-{field}.json`.

### public API (`__init__.py`)

Six new sync wrappers:

- `push_changelog() → PushResult`
- `pull_changelog() → PullResult`
- `create_snapshot() → None`
- `list_conflicts() → list[ConflictRecord]`
- `resolve_conflict(uid, field, winning_value) → None`
- `restore_reference(citekey) → Result`

`resolve_conflict` writes a new authoritative `update_reference` entry with a fresh HLC
timestamp and removes the `ConflictRecord` from the store.

## out of scope

- rsync adapter — deferred; S3-compatible covers all v1 deployment targets.
- Blob sync (`blobs/`, `link_file`, `unlink_file`, `prefetch_blobs`) — phase 2.
- Garage federated adapter — phase 2.
- Automatic snapshot triggers — manual only for now.
- Polling daemon / real-time pull — manual pull only.
- Snapshot signing — deferred to phase 2.
- Storage credential revocation — coordinator responsibility, out of band.
