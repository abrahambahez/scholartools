# rfc: peer identity and change log verification

**status:** draft
**date:** 2026-03-14
**author:** abrahambahez
**context:** FLACSO water sources index, multi-scholar curation
**depends on:** [RFC 001](001-distributed-sync.md) — change log schema and sync protocol

---

## summary

Define the identity model, key management, peer registration lifecycle, and pull-time
verification rules for the distributed sync layer introduced in RFC 001. Every change
log entry carries a cryptographic signature; pull rejects any entry that cannot be
verified against the registered peer directory before merge logic runs.

This RFC is a prerequisite for phase 1 of RFC 001. The `peers/` directory and signed
entry schema described here must be in place before any multi-peer deployment.

## motivation

RFC 001 left open whether `peer_id` in config is sufficient for identity, or whether
FLACSO requires verifiable attribution per change. For a shared academic index:

- **audit trail**: knowing *which device* submitted a change matters for error correction
  and accountability, especially when curating sensitive or contested sources.
- **tamper resistance**: without signatures, any peer with storage credentials can
  fabricate or alter another peer's change log entries.
- **revocation**: if a device is compromised or a contributor leaves the project, their
  future writes must be rejectable without rewriting history.

The append-only, local-first architecture of RFC 001 is compatible with a
signature-and-directory model that adds these properties without requiring a central
authority online at write time.

## proposed design

### identity model

Each contributor is identified by a `peer_id` (a human-readable string chosen at
registration, e.g. `scholar-abc`). A contributor working across multiple devices
registers each device separately under the same `peer_id`. Each device holds its own
Ed25519 keypair. The private key never leaves the device that generated it.

Every change log entry carries a `peer_id`, a `device_id`, and an Ed25519 signature
over its canonical payload. Pull rejects entries with missing or invalid signatures
before any merge logic runs.

### keypair format

Keys are stored as raw 32-byte Ed25519 keys, base64url-encoded (no padding), under
`~/.config/scholartools/keys/{peer_id}/{device_id}.key` (private) and
`~/.config/scholartools/keys/{peer_id}/{device_id}.pub` (public). This path is derived
from `CONFIG_PATH.parent / "keys"` — never from a library's `data_dir`, so the identity
is user-scoped and machine-local regardless of which library the user is working with.
The private key file is created with mode `0600`. Public keys are shared as identity
files during onboarding.

### canonical payload for signing

The canonical payload is the change log entry JSON object with all fields **except**
`signature`, serialized with sorted keys and no extra whitespace (`separators=(',', ':')`,
`sort_keys=True`). The signature covers the UTF-8 bytes of this string.

### roles

**admin peer** — one per deployment, with an optional secondary for continuity (see
[open questions](#open-questions)). The only peer authorized to write to the `peers/`
directory in shared storage. Responsible for registering and revoking peers and devices.
The admin keypair is the root of trust for the deployment.

**regular peer** — any scholar contributor. Write access is scoped to their own
`changes/{peer_id}/` prefix. Cannot modify peer registration records.

### storage layout

The `peers/` directory lives at the shared-root alongside `changes/` and `snapshots/`
(see RFC 001 storage layout):

```
{shared-root}/
    peers/
        _admin              ← self-signed admin registration record
        {peer_id}           ← peer record signed by admin
    changes/
    snapshots/
```

Each file in `peers/` is a JSON registration record. Regular peer records are signed
by the admin. The admin's own record (`_admin`) is self-signed.

### peer registration record format

```json
{
  "peer_id": "scholar-abc",
  "devices": [
    {
      "device_id": "laptop-primary",
      "public_key": "<base64url Ed25519 public key>",
      "registered_at": "2026-03-14T10:00:00Z",
      "revoked_at": null
    }
  ],
  "registered_at": "2026-03-14T10:00:00Z",
  "revoked_at": null,
  "signature": "<base64url Ed25519 signature by admin over canonical payload>"
}
```

The canonical payload for the record signature is the record JSON with all fields
except `signature`, serialized with sorted keys and no extra whitespace.

The admin record (`_admin`) has an additional `role: "admin"` field and is
self-signed using the admin's own keypair.

### peer directory load

Pull loads the entire `peers/` directory at the start of each sync session. It builds
an in-memory map of `(peer_id, device_id) → public_key`, filtering out any device
entries where `revoked_at` is set. This map is used for signature verification during
the same session and discarded afterward — it is never cached locally between sessions.

### verification rules

Pull applies these rules in order before processing any change log entry:

1. The `(peer_id, device_id)` pair must exist in the peers directory.
2. The pair must not have `revoked_at` set.
3. The signature must verify against the registered Ed25519 public key for that pair.
4. Entries failing any rule are rejected: written to a local `rejected/` directory as
   `{hlc_timestamp}-{peer_id}-{device_id}.json` for operator review. They are never
   applied to the local library.

### onboarding a new peer

1. The scholar runs `peer_init(peer_id, device_id)` on their device. This generates a
   local Ed25519 keypair, stores the private key at `keys/{peer_id}/{device_id}.key`
   (mode `0600`), and returns a public identity record for sharing.
2. The scholar sends the public identity record to the project coordinator out of band
   (email, chat — any channel).
3. The coordinator runs `peer_register(identity)`, which signs the registration record
   with the admin keypair and writes it to `peers/{peer_id}` in shared storage. From
   this moment the peer is authorized.
4. The coordinator shares storage access credentials with the scholar out of band.
   Credentials are scoped **per peer** (not per device) — one set of S3/rsync
   credentials covers all devices under the same `peer_id`.
5. The scholar runs `pull()` to bootstrap their local library from the latest snapshot.

### adding a device to an existing peer

1. The scholar runs `peer_init(peer_id, device_id)` on the new device with a new
   `device_id`. A new keypair is generated for this device only.
2. The scholar sends the new device's public identity record to the coordinator.
3. The coordinator runs `peer_add_device(peer_id, device_identity)`, which appends the
   new device entry to the existing peer record and re-signs it.

Storage credentials do not change — the peer already has access.

### revoking a peer or device

- `peer_revoke_device(peer_id, device_id)` — marks the device entry with a
  `revoked_at` timestamp in the peer record and re-signs. The entry is never deleted,
  preserving the audit trail.
- `peer_revoke(peer_id)` — marks all devices under the `peer_id` as revoked and
  re-signs. The coordinator should also revoke the peer's storage credentials out of
  band (S3 IAM, SSH key removal).
- Pull rejects any entry signed by a revoked `(peer_id, device_id)` pair.
- Historical entries already applied to the local library before revocation remain
  valid — the log is never rewritten.

### new public API functions

- `peer_init(peer_id, device_id) → PeerIdentity` — generates a local keypair and
  returns a public identity record for sharing with the coordinator.
- `peer_register(identity: PeerIdentity) → None` — admin only. Signs the record and
  writes it to `peers/` in shared storage.
- `peer_add_device(peer_id, device_identity: DeviceIdentity) → None` — admin only.
  Appends a device entry to an existing peer record and re-signs.
- `peer_revoke_device(peer_id, device_id) → None` — admin only. Sets `revoked_at` on
  the device entry and re-signs.
- `peer_revoke(peer_id) → None` — admin only. Sets `revoked_at` on all devices and
  re-signs.

All admin functions verify that the local keypair corresponds to the `_admin` record
before writing. Non-admin invocations return an error result without touching storage.

### new models (models.py)

```python
class DeviceIdentity(BaseModel):
    device_id: str
    public_key: str          # base64url Ed25519 public key
    registered_at: datetime
    revoked_at: datetime | None = None

class PeerRecord(BaseModel):
    peer_id: str
    devices: list[DeviceIdentity]
    registered_at: datetime
    revoked_at: datetime | None = None
    role: str = "peer"       # "admin" for the _admin record
    signature: str           # base64url Ed25519 signature

class PeerIdentity(BaseModel):
    peer_id: str
    device: DeviceIdentity
```

### architecture fit

Peer management is implemented as a set of functions in a new
`src/scholartools/services/peers.py` module and a new
`src/scholartools/adapters/peer_directory.py` adapter. The adapter handles reading and
writing the `peers/` directory through the existing `RemoteSyncPort`. The service
functions contain the key generation and signature logic.

```
peer_init / peer_register / ...       ← services/peers.py
    └── PeerDirectoryAdapter          ← adapters/peer_directory.py
            └── RemoteSyncPort        (existing — rsync | s3)
```

The pull path in `SyncCompositeAdapter` gains a `verify_entry(entry, peer_map)` step
that calls into a pure function in `services/peers.py`. No new port is required.

The `cryptography` library (PyCA) is the only new dependency. It is already widely
used in the Python ecosystem, has no system-level requirements, and is available on all
target platforms. Explicit approval is required before adding it to `pyproject.toml`.

## what this does not solve

**storage credential management.** Revoking a peer's signing key prevents future
verified writes, but does not prevent the peer from writing unverified entries or
reading shared storage. Storage credentials (S3 IAM, SSH keys) must be revoked out of
band by the coordinator. This RFC does not automate that step.

**admin key backup.** If the admin private key is lost, no new peers can be registered
or revoked. Key backup strategy (e.g., encrypted export to a second admin device) is
the coordinator's responsibility and is not enforced by the protocol.

**entry confidentiality.** Signatures provide integrity and attribution, not
confidentiality. Change log entries are readable by anyone with storage access. If
the shared storage backend requires access control on reads, that is a backend
configuration concern.

## open questions

1. **Secondary admin.** For FLACSO's team size, a single admin is a continuity risk if
   the coordinator is unavailable. Recommendation: support up to two admin peers
   (primary and secondary), each with their own keypair and self-signed `_admin`
   record. The secondary is registered by the primary admin. Pull trusts any signature
   from a record with `role: "admin"`. Should this be in scope for this RFC or deferred?

2. **Rejection notification.** When a pull encounters a rejected entry, is writing to
   the local `rejected/` log sufficient, or should the coordinator receive an
   out-of-band alert (e.g., a flag in the next `pull()` result)? For FLACSO's
   cadence, surfacing rejections in the `pull()` return value is likely sufficient —
   a separate notification daemon is out of scope.

3. **Snapshot signing.** Should snapshots (RFC 001) carry an admin signature to prevent
   a compromised bootstrap? Not required for phase 1, but worth deciding before
   phase 2 when blob distribution makes snapshot integrity more critical.
