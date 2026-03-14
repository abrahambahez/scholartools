# rfc: append-only distributed sync for scholartools

**status:** revised draft
**date:** 2026-03-11
**author:** abrahambahez
**context:** FLACSO water sources index, multi-scholar curation

---

## summary

Add a distributed sync layer to scholartools using an append-only change log and content-addressed blob storage. Local-first behavior is preserved — scholars work offline against their local library, and sync is an explicit operation. No central database, no coordination server.

The sync backend is infrastructure-agnostic: the same protocol runs on managed cloud storage, a self-hosted Linux server, or a federated cluster. Stakeholders choose the deployment model that matches their ownership requirements.

This RFC describes the complete design in two phases:

- **phase 1 — metadata sync**: change log, uid cascade, conflict resolution, soft-delete, rsync and S3/MinIO adapters. No blob distribution.
- **phase 2 — blob sync**: content-addressed PDF distribution, pull cache, Garage federated adapter.

Each phase maps to one or more `docs/feats/` entries and sequential specs. Implementation runs on a dedicated branch and merges to main only after both phases pass end-to-end testing.

## prerequisite

The `deduplication` feature (`feature_list.json`) must be `passes: true` before implementation of phase 1 begins. The uid cascade and cross-peer merge semantics depend on reliable local duplicate detection — if local dedup has gaps, sync will amplify them across all peers.

## motivation

The FLACSO project requires multiple scholars to independently curate and contribute references to a shared index. The current architecture assumes a single writer per library. Two problems need solving:

- **metadata sync** — changes from different peers need to merge without conflicts
- **file distribution** — linked PDFs need to be accessible across peers without duplicating storage or relying on local paths

## proposed design

### storage layout

**Phase 1** (metadata only):

```
{shared-root}/
    peers/
        _admin
        {peer_id}
    changes/{peer_id}/{hlc_timestamp}.json
    snapshots/{timestamp}.json
```

**Phase 2** adds:

```
{shared-root}/
    blobs/{sha256}
```

The `peers/` directory is managed exclusively by the admin peer. See [RFC 002](002-peer-management.md) for the full peer registration and verification design.

`{shared-root}` maps to a bucket, a directory on a remote server, or a path in a federated cluster depending on the chosen backend (see [deployment tiers](#deployment-tiers)).

### change log entries

Change log entries are append-only JSON records written as **one file per push** (not one file per operation). Writing a single file per push makes rsync effectively atomic — simultaneous pushes from different peers produce distinct files that interleave cleanly during pull, eliminating the race condition inherent in per-operation file writes.

The complete set of ops:

| op | phase | description |
|---|---|---|
| `add_reference` | 1 | add a new record |
| `update_reference` | 1 | update one or more fields of an existing record |
| `delete_reference` | 1 | soft-delete: sets `deleted: true`, data preserved |
| `restore_reference` | 1 | clears `deleted` flag, restores record to library |
| `link_file` | 2 | associate a blob with a record via `blob_ref` |
| `unlink_file` | 2 | disassociate a blob from a record |

Example entry (phase 1):

```json
{
  "op": "add_reference",
  "uid": "a3f9c2d1",
  "uid_confidence": "authoritative",
  "citekey": "perez2024",
  "data": { "..." : "..." },
  "peer_id": "scholar-abc",
  "device_id": "laptop-primary",
  "timestamp_hlc": "2026-03-11T10:00:00.000Z-0001-scholar-abc",
  "signature": "<base64-encoded Ed25519 signature over canonical payload>"
}
```

The canonical payload for signing is the JSON object with all fields except `signature`, serialized with sorted keys and no extra whitespace.

Example entry (phase 2, `link_file`):

```json
{
  "op": "link_file",
  "uid": "a3f9c2d1",
  "blob_ref": "sha256:e3b0c44298fc1c149afbf4c8996fb924",
  "peer_id": "scholar-abc",
  "device_id": "laptop-primary",
  "timestamp_hlc": "2026-03-11T10:05:00.000Z-0001-scholar-abc",
  "signature": "<base64-encoded Ed25519 signature over canonical payload>"
}
```

Pull verifies `(peer_id, device_id, signature)` against the `peers/` directory before processing any entry. Verification rules and rejection behavior are specified in [RFC 002](002-peer-management.md).

**Soft-delete and restore.** A `delete_reference` entry sets `deleted: true` on the record in the local library. The record and its data are preserved. A `restore_reference` entry clears the flag. Deleted records are excluded from all list and filter operations by default; they remain visible under an explicit `include_deleted=True` flag and can be restored via `restore_reference(citekey)`. Hard delete (permanent removal from the log) is not supported by this protocol.

**Delete vs. concurrent edit.** If a peer receives a `delete_reference` entry for a uid that has a local edit with a newer HLC timestamp than the delete, the delete is applied but the local edit is written to the `conflicts/` store rather than discarded. The reviewer sees: "this record was deleted by peer X, but you have a newer local edit — keep deletion, or restore and apply your edit?"

### record identity: the uid field

Every reference carries a `uid` field — a short hex string computed at intake (the moment a record is first normalized to CSL-JSON and enters staging) and never recomputed. It is the stable identity key used by the sync layer for deduplication and merge. The citekey remains the human-readable local alias and the primary key for all public API calls.

If a tier-2 record later receives an authoritative identifier (DOI, arXiv, ISBN), the uid is **not** updated — the new identifier is stored in the record but the original uid remains the merge key.

uid generation follows a priority cascade:

**tier 1 — authoritative external identifiers** (~85% of academic literature)

```python
if doi:   uid = sha256(f"doi:{doi.lower().strip()}")[:16]
if arxiv: uid = sha256(f"arxiv:{arxiv.strip()}")[:16]
if isbn:  uid = sha256(f"isbn:{normalize_isbn(isbn)}")[:16]
```

**tier 2 — semantic hash from canonical fields** (grey literature, reports, datasets)

```python
canonical = {
    "title": normalize_text(record.title),
    "year":  record.issued.date_parts[0][0],
    "first_author": normalize_text(record.author[0].family),
    "type": record.type,
}
uid = sha256(json.dumps(canonical, sort_keys=True))[:16]
```

#### normalization spec (canonical, versioned at this revision)

`normalize_text` is a deterministic function applied identically on all peers. Its rules are frozen at this revision of the RFC — any change constitutes a new normalization version and invalidates all existing tier-2 uids:

1. Apply Unicode NFC normalization
2. Lowercase all characters
3. Remove all Unicode punctuation characters (category `P*`) and symbols (category `S*`)
4. Collapse all whitespace sequences (space, tab, newline) to a single ASCII space
5. Strip leading and trailing whitespace

`normalize_isbn` strips all hyphens and spaces and converts ISBN-10 to ISBN-13.

A `uid_confidence` field accompanies the uid: `"authoritative"` for tier 1, `"semantic"` for tier 2.

**`uid_confidence: "semantic"` records are held in staging by default** and require explicit human confirmation before merge into the shared index. This prevents noisy tier-2 false matches from propagating to all peers.

**record shape:**

```json
{
  "uid": "a3f9c2d1",
  "uid_confidence": "authoritative",
  "citekey": "vaswani2017",
  "type": "article-journal",
  "title": "Attention Is All You Need",
  "DOI": "10.48550/arXiv.1706.03762"
}
```

**known limitations of tier 2:** preprint and published versions of the same paper may produce different uids if their canonical fields differ. Missing author or year fields degrade the hash toward title-only, increasing collision risk. For a curated index with human review in the loop, this is acceptable.

### sync protocol

1. **push** — run `merge()` on any local staged work, then sign and write all new local change log entries as a single file to `changes/{peer_id}/{hlc_timestamp}.json` on the shared backend
2. **pull** — fetch all change log files newer than the last known HLC fence; verify each entry's `(peer_id, device_id, signature)` against the `peers/` directory (see [RFC 002](002-peer-management.md)); replay verified entries against the local library; write rejected entries to a local `rejected/` log
3. **merge** — the existing `merge()` API is the primitive for committing local staged work before a push

**Conflict detection.** During pull, for each incoming `update_reference` entry the sync layer compares incoming field values against local field values for the same uid. A conflict is raised when:

- the same field has different values in the incoming and local records, **and**
- the HLC timestamps of the two versions are within a configurable window (default: 60 seconds)

Outside the window, LWW applies without conflict — the newer timestamp wins silently.

**Conflict resolution — local `conflicts/` store.** When a conflict is detected:

1. The local library record is not overwritten
2. A conflict record is written to a local `conflicts/` store:
   ```json
   {
     "uid": "a3f9c2d1",
     "field": "author",
     "local_value": ["..."],
     "local_timestamp_hlc": "...",
     "remote_value": ["..."],
     "remote_timestamp_hlc": "...",
     "remote_peer_id": "scholar-xyz"
   }
   ```
3. The agent/human calls `list_conflicts()` to inspect outstanding conflicts
4. The agent/human calls `resolve_conflict(uid, field, winning_value)` to choose a value
5. Resolution writes a new authoritative `update_reference` entry with a fresh HLC timestamp that wins all future LWW for that field
6. The conflict record is removed from the store

The `conflicts/` store is local to each peer — it is not synced. Conflict resolution is always a local operation.

### snapshots

Snapshots are periodic full-library exports used to bootstrap new peers without replaying the entire change log.

**Snapshot generation.** A snapshot captures the library state and records the HLC fence at the moment of generation — the HLC timestamp of the most recent change log entry processed before the snapshot was written.

**Bootstrap protocol for new peers:**

1. Pull the latest snapshot from `snapshots/`
2. Read its `fence_hlc` field
3. Pull all change log entries where `timestamp_hlc >= fence_hlc`
4. Replay those entries on top of the snapshot

Overlapping entries (already included in the snapshot state) are idempotent — an `add_reference` or `update_reference` for a uid whose local record already has a newer HLC timestamp is a no-op under LWW.

**Snapshot frequency.** Triggered manually via `create_snapshot()`. Automatic triggers are a future option — not in scope for either phase.

### architecture fit

The sync layer is a **composite adapter** — it is not a drop-in replacement for the existing local JSON storage port. It holds two sub-adapters: a local adapter (offline working copy and read cache) and a pluggable remote sync adapter. Services and the public API remain unchanged.

```
public API (unchanged)
    └── services (unchanged)
            └── SyncCompositeAdapter       ← NEW: implements StoragePort
                    ├── LocalJsonAdapter   (read cache / offline working copy)
                    └── RemoteSyncPort     (pluggable — rsync | s3 | garage)
```

`SyncCompositeAdapter` implements the existing `StoragePort` interface. The service layer never knows it is running against a composite. `RemoteSyncPort` is a new port interface with two implementations in phase 1 (rsync, S3/MinIO) and a third in phase 2 (Garage).

A `conflicts/` directory is added to the local data layout — no configuration required.

The sync adapter is configured via `config.json`:

```json
{ "sync": { "backend": "s3", "endpoint": "https://minio.example.org", "bucket": "scholartools" } }
```

```json
{ "sync": { "backend": "rsync", "host": "user@server.example.org", "path": "/srv/scholartools-shared" } }
```

### deployment tiers

Phase 1 ships three adapters (rsync, MinIO/self-hosted S3, managed S3). Phase 2 adds Garage.

| tier | infrastructure | phase | suitable for |
|---|---|---|---|
| minimal | rsync over SSH | 1 | individuals, maximum simplicity |
| self-hosted S3 | MinIO on a VPS | 1 | research groups, cost-sensitive |
| managed | AWS S3, Backblaze B2 | 1 | institutions, low ops burden |
| federated | Garage cluster | 2 | activist networks, no single operator |

**rsync over SSH** requires no special software. Push writes a single JSON file per session: `rsync -av ./changes/peer-id/timestamp.json user@server:/srv/scholartools-shared/changes/peer-id/`. Single-file writes via rsync are atomic at the filesystem level on Linux.

**MinIO** is a single binary, Apache 2.0 licensed. The S3 adapter covers AWS S3, Backblaze B2, and MinIO with no code changes — only the endpoint and credentials differ in config.

**Garage** is designed for small distributed clusters where nodes are contributed by multiple participants — no single operator controls the data, resilient to any one node going offline or being seized. MIT licensed. Deferred to phase 2.

## implementation phases

### phase 1 — metadata sync

Scope: change log (one file per push), uid cascade (tier 1 + tier 2), normalization spec, conflict detection and `conflicts/` store, soft-delete and restore, snapshot protocol with HLC fence, rsync adapter, S3/MinIO adapter, `SyncCompositeAdapter`.

New public API functions: `push()`, `pull()`, `create_snapshot()`, `list_conflicts()`, `resolve_conflict()`, `restore_reference()`.

Phase 1 alone satisfies the FLACSO metadata curation workflow. PDFs are not distributed — scholars share metadata; files remain local.

### phase 2 — blob sync

Scope: `blobs/{sha256}` storage layout, `link_file` and `unlink_file` change log ops, pull cache for local file access, Garage adapter.

`link_file(citekey, path)` gains an upload step:

1. Hash file locally → sha256
2. HEAD `blobs/{sha256}` on the remote — skip upload if already present
3. Upload if missing
4. Write `link_file` change log entry with `blob_ref: sha256`

On the read path, `get_file(citekey)` gains an `ensure_local()` step: if the file is absent from the local pull cache, fetch from `blobs/{sha256}` before returning the path.

**Blob sync is lazy by design.** `pull()` never fetches blob content — it only records `blob_ref` values in the local library. Files are downloaded on first access via `get_file()`. This keeps daily pull/push cycles lightweight regardless of how many PDFs the shared index contains. A scholar working primarily with metadata never accumulates blobs they don't open.

For scholars who need a full local copy before going offline (e.g., fieldwork), an explicit `prefetch_blobs(citekeys=None)` function downloads all referenced blobs for the given citekeys, or the entire library if called with no arguments.

## what this does not solve

**preprint vs published identity.** The uid cascade treats a preprint and its published version as different records if their DOIs differ. For FLACSO's water index, treating them as distinct is probably correct — but an explicit policy should be documented before onboarding contributors.

**access control.** Access control is backend-specific. S3 and MinIO use bucket policies and IAM credentials per peer. rsync relies on SSH key authorization. Cryptographic entry signing and peer registration are specified in [RFC 002](002-peer-management.md).

**real-time collaboration.** This design targets low-frequency, offline-first curation. If that requirement emerges, a full CRDT document model (e.g., Automerge) would be the appropriate next step — the sync layer abstraction described here would accommodate it without changing the public API.

## open questions

1. Should snapshots be generated automatically (e.g., every N changes) or remain manual-only?
2. ~~Is `peer_id` in config sufficient for identity, or does FLACSO require verifiable attribution per change?~~ Resolved: Ed25519-signed entries with per-device keypairs. See [RFC 002](002-peer-management.md).
3. What is the acceptable lag between a scholar's push and another's pull — is periodic manual pull sufficient, or does FLACSO need a polling daemon?
4. Is there a FLACSO-specific identifier (institutional record ID, project code) that should be promoted to tier 1 in the uid cascade?

## feedback requested

- Does the two-phase split (metadata now, blobs later) work for FLACSO's near-term workflow?
- Is the `staging → push` mental model intuitive for scholars who are not developers?
- Any concerns about storing PDFs in S3 under a content-addressed scheme from a rights or attribution perspective?
- Is the 60-second conflict detection window appropriate for the FLACSO curation cadence, or should it be configurable per deployment?
