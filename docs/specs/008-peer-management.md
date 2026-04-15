# spec: 008-peer-management

## findings

From docs/rfc/002-peer-management.md: Peer management is the identity and verification
layer required for phase 1 of the distributed sync protocol (RFC 001). Each contributor
is identified by a `peer_id` (human-readable, e.g. `scholar-abc`) and can register
multiple devices, each with its own Ed25519 keypair. Change log entries are signed and
pull-time verified against the peer directory before merge logic runs.

Key design decisions:
- Identity is `(peer_id, device_id)`; keys are Ed25519, one keypair per device.
- Private keys stored at `~/.config/scholartools/keys/{peer_id}/{device_id}.key` (mode 0600) — user-scoped, machine-local, outside any library `data_dir`.
- Admin peer is the sole writer to `peers/` in shared storage.
- All admin functions verify the local keypair matches the `_admin` record before writing.
- Pull loads the peers directory, filters revoked devices, builds an in-memory map, and
  verifies entry signatures before any merge logic runs.
- Canonical payload for signing: JSON with sorted keys, no extra whitespace, `signature`
  field excluded.
- `peers/` is a flat directory of JSON records; no database, no coordination server.

## objective

Implement the peer identity and verification layer from RFC 002. Key generation, peer
registration, device management, and signature verification live in three layers:
`models.py` (new Pydantic types), `services/peers.py` (crypto and lifecycle logic),
and `adapters/peer_directory.py` (read/write `peers/` through the filesystem).

The feature is testable without any remote sync infrastructure — all operations work
against a local directory standing in as shared storage. The `RemoteSyncPort` interface
does not need to exist yet; the adapter receives a directory path.

Task-11 (wiring `verify_entry` into pull) is the only task that touches sync and should
be treated as a forward-compatibility stub — it does not require `SyncCompositeAdapter`
to be complete.

## acceptance criteria (EARS format)

- WHEN `peer_init(peer_id, device_id)` is called, the system MUST generate a new Ed25519
  keypair, store the private key at
  `~/.config/scholartools/keys/{peer_id}/{device_id}.key` (mode 0600), and return a
  `PeerIdentity` model containing the base64url-encoded public key. The key path is
  derived from `CONFIG_PATH.parent / "keys"`, never from `data_dir`.
- WHEN `peer_init` is called for a `(peer_id, device_id)` pair that already has a local
  key file, the system MUST return an error result without overwriting the existing key.
- WHEN `peer_register(identity)` is called without a local admin keypair present, the
  system MUST return an error result without writing to storage.
- WHEN `peer_register(identity)` is called with a valid admin keypair, the system MUST
  sign the peer record with the admin's private key, write it to `peers/{peer_id}` in the
  shared directory, and return a success result.
- WHEN `peer_add_device(peer_id, device_identity)` is called with a valid admin keypair,
  the system MUST append the device entry to the existing peer record, re-sign the record,
  and write it back.
- WHEN `peer_revoke_device(peer_id, device_id)` is called with a valid admin keypair, the
  system MUST set `revoked_at` to the current UTC timestamp on the device entry and
  re-sign the peer record.
- WHEN `peer_revoke(peer_id)` is called with a valid admin keypair, the system MUST set
  `revoked_at` on all device entries under that peer and re-sign the peer record.
- WHEN any admin function is called without a valid admin keypair, the system MUST return
  an error result without touching storage.
- WHEN `load_peer_directory(peers_dir)` is called, the system MUST return a
  `dict[tuple[str, str], bytes]` mapping `(peer_id, device_id)` to raw public key bytes,
  excluding all device entries where `revoked_at` is set.
- WHEN `verify_entry(entry, peer_map)` is called, the system MUST apply rules in order:
  (1) `(peer_id, device_id)` exists in the map; (2) signature verifies against the
  registered public key. Failure at any rule MUST return an error result.
- WHEN an entry fails verification, the system MUST write it to
  `rejected/{hlc_timestamp}-{peer_id}-{device_id}.json` in the local data directory and
  never apply it to the library.
- WHEN a peer record is signed, the canonical payload MUST be the record dict serialized
  with `json.dumps(record, sort_keys=True, separators=(',', ':'))` excluding the
  `signature` field. Any deviation from this spec invalidates all existing signatures.
- WHEN the admin record is initialized, it MUST include `role: "admin"` and be
  self-signed using the admin's own keypair.

## tasks

- [ ] task-01: add `DeviceIdentity`, `PeerRecord`, `PeerIdentity` to `models.py`;
  `registered_at`/`revoked_at` as `datetime | None`; `role` defaults to `"peer"`
  (blocks: nothing)

- [ ] task-02: add `cryptography` to `pyproject.toml` and run `uv sync` — requires
  explicit user approval before executing (blocks: nothing)

- [ ] task-03: `services/peers.py` — `_canonical(record: dict) -> bytes` (sorted-key
  JSON, no `signature` field), `_sign(payload: bytes, private_key: bytes) -> str`
  (base64url), `_verify(payload: bytes, signature: str, public_key: bytes) -> bool`
  (blocks: task-02)

- [ ] task-04: `services/peers.py` — `peer_init(peer_id, device_id, ctx) -> Result`
  checks key file does not exist, generates Ed25519 keypair, writes private key (mode
  0600) to `CONFIG_PATH.parent / "keys" / peer_id / device_id + ".key"`, returns
  `PeerIdentity` (blocks: task-01, task-03)

- [ ] task-05: `adapters/peer_directory.py` — `load_peer_directory(peers_dir: Path) ->
  dict[tuple[str, str], bytes]` reads all JSON files in `peers/`, skips revoked devices,
  decodes base64url public keys to raw bytes (blocks: task-01)

- [ ] task-06: `services/peers.py` — `peer_register(identity, ctx) -> Result` loads
  local admin keypair, verifies it against `_admin` record in shared directory, builds
  and signs a `PeerRecord`, writes to `peers/{peer_id}` (blocks: task-03, task-04,
  task-05)

- [ ] task-07: `services/peers.py` — `peer_add_device(peer_id, device_identity, ctx) ->
  Result` loads existing peer record, appends device entry, re-signs, writes back
  (blocks: task-06)

- [ ] task-08: `services/peers.py` — `peer_revoke_device(peer_id, device_id, ctx) ->
  Result` and `peer_revoke(peer_id, ctx) -> Result`; set `revoked_at`, re-sign, write
  back (blocks: task-06)

- [ ] task-09: `services/peers.py` — `verify_entry(entry: dict, peer_map: dict) ->
  Result` checks presence, then signature; returns error result on any failure (blocks:
  task-03, task-05)

- [ ] task-10: rejection log — write failed entries to
  `rejected/{hlc_timestamp}-{peer_id}-{device_id}.json` in local data dir; add
  `rejected_dir` to `LibraryCtx` or derive from existing `data_dir` (blocks: task-09)

- [ ] task-11: forward-compatibility stub — `services/peers.py` exports a
  `make_pull_verifier(peers_dir) -> Callable[[dict], Result]` that combines
  `load_peer_directory` + `verify_entry`; no `SyncCompositeAdapter` required yet
  (blocks: task-09, task-10)

- [ ] task-12: `__init__.py` — sync wrappers for `peer_init`, `peer_register`,
  `peer_add_device`, `peer_revoke_device`, `peer_revoke`; export `PeerIdentity`,
  `PeerRecord`, `DeviceIdentity` (blocks: task-04, task-06, task-07, task-08)

- [ ] task-13: unit tests `tests/unit/test_peers.py` — keypair generation, canonical
  payload stability, sign/verify round-trip, revocation filtering in
  `load_peer_directory`, `verify_entry` pass/fail cases; all with temp dirs (blocks:
  task-03 through task-11)

- [ ] task-14: integration test `tests/integration/test_peer_lifecycle.py` — full
  admin-init → peer-register → add-device → revoke-device → verify-entry flow against
  a tmp shared dir; mark `@pytest.mark.integration` (blocks: task-13)

- [ ] task-15: full test suite green; no regressions on existing tests (blocks: task-14)

## risks

- **Cryptography dependency**: `cryptography` (PyCA) is the only new external dep; no
  system-level requirements on target platforms. Task-02 requires explicit approval.

- **Canonical payload is immutable**: any change to `sort_keys`, `separators`, or field
  exclusion in `_canonical()` invalidates all existing signatures. Treat as a versioned
  protocol constant, not implementation detail.

- **Private key loss is unrecoverable**: there is no key derivation or backup mechanism.
  Lost key → revoke device → re-register with a new `device_id`. Document as a
  critical bootstrap warning.

- **Admin key loss blocks all future peer management**: if the admin private key is lost,
  no new peers can register or be revoked. Out of scope for this spec; FLACSO must
  establish a backup strategy before phase 1 deployment.

- **Storage credential revocation is out of band**: revoking a signing key prevents
  verified writes; it does not prevent unverified writes or reads. S3/SSH credentials
  must be revoked separately by the coordinator.
