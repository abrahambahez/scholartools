# feat 008: distributed sync phase 1 — append-only change log, push/pull, conflict resolution

version: 0.1
status: deprecated

> **Deprecated (v0.13.0, spec 027):** Distributed sync was removed from core to enforce the portability invariant. The `minio` dependency (S3-compatible object storage) does not belong in the core package, and the HLC/change-log infrastructure it required would make core non-portable. All sync infrastructure will be re-introduced as a future `loretools-sync` plugin. This document is preserved as the design reference for that future work.

---

## context

Full design is in `docs/rfc/001-distributed-sync.md`. Peer identity and pull
verification are covered by feat 007. UID generation and deduplication are covered
by feat 006 and remain implemented in core.

This feat covers the sync layer itself: composite adapter, HLC timestamps, change log
format, push/pull protocol, LWW merge, conflict store, soft-delete, and snapshots.

**Backend scope (proposed):** S3-compatible only (AWS S3, Backblaze B2, MinIO). A single
adapter covers all three via endpoint override.

## proposed design

### HLC timestamps

New module `services/hlc.py`. Implements Hybrid Logical Clock: `now(peer_id) -> str`
returns a sortable string `{iso_utc}-{counter:04d}-{peer_id}`.

### change log models

```python
class ChangeLogEntry(BaseModel):
    op: Literal["add_reference", "update_reference", "delete_reference", "restore_reference"]
    uid: str
    uid_confidence: Literal["authoritative", "semantic"]
    citekey: str
    data: dict | None = None
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

### composite adapter

`adapters/sync_composite.py` holds a `LocalJsonAdapter` and a `RemoteSyncPort` instance.
Services see only `StoragePort` — no sync-specific logic leaks upward.

**push_changelog:** collects local `ChangeLogEntry` records not yet pushed, signs each
entry, writes to `changes/{peer_id}/{hlc_timestamp}.json`.

**pull_changelog:** loads peer directory, lists new `changes/` keys, downloads and
verifies each entry, replays in HLC order against the local library (LWW per field).

**LWW rule:** for `update_reference`, the entry with the greater `timestamp_hlc` string
(lexicographic) wins. Within 60 s of a conflict, a `ConflictRecord` is written and the
local value is preserved.

### sync config (proposed)

```json
{
  "sync": { "endpoint": "https://minio.example.org", "bucket": "scholartools", "access_key": "...", "secret_key": "..." },
  "peer": { "peer_id": "sabhz", "device_id": "laptop" }
}
```

### S3 adapter (proposed)

`adapters/s3_sync.py` implementing `RemoteSyncPort` via `minio>=7.0.0`.
`minio` as an optional `sync` extras group.

### public API (proposed, not implemented)

- `push_changelog() → PushResult`
- `pull_changelog() → PullResult`
- `create_snapshot() → None`
- `list_conflicts() → list[ConflictRecord]`
- `resolve_conflict(uid, field, winning_value) → None`
- `restore_reference(citekey) → Result`

## out of scope for this feat

- rsync adapter
- Blob sync — feat 009
- Garage federated adapter
- Automatic snapshot triggers
- Polling daemon / real-time pull
