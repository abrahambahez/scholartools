# feat 007: peer identity and change log verification

version: 0.1
status: deprecated

> **Deprecated (v0.13.0, spec 027):** Peer management was removed from core to enforce the portability invariant. The `cryptography` (Ed25519) dependency it required does not belong in the core package. All peer identity, keypair management, and signature verification logic will be re-introduced as part of a future `loretools-sync` plugin. This document is preserved as the design reference for that future work.

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
`~/.config/scholartools/keys/{peer_id}/{device_id}.pub` (public). The private key file
is created with mode `0600`.

### canonical payload for signing

The canonical payload is the change log entry JSON object with all fields **except**
`signature`, serialized with sorted keys and no extra whitespace (`separators=(',', ':')`,
`sort_keys=True`). The signature covers the UTF-8 bytes of this string.

### roles

**admin peer** — one per deployment. The only peer authorized to write to the `peers/`
directory in shared storage. Responsible for registering and revoking peers and devices.

**contributor** — any scholar contributor. Write access is scoped to their own
`changes/{peer_id}/` prefix. Cannot modify peer registration records.

### storage layout

```
{shared-root}/
    peers/
        _admin              ← self-signed admin registration record
        {peer_id}           ← peer record signed by admin
    changes/
    snapshots/
```

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

### verification rules

Pull applies these rules in order before processing any change log entry:

1. The `(peer_id, device_id)` pair must exist in the peers directory.
2. The pair must not have `revoked_at` set.
3. The signature must verify against the registered Ed25519 public key for that pair.
4. Entries failing any rule are rejected: written to a local `rejected/` directory for operator review.

### new public API functions (proposed, not implemented)

- `peer_init(peer_id, device_id) → PeerIdentity` — generates a local keypair
- `peer_register(identity: PeerIdentity) → None` — admin only
- `peer_add_device(peer_id, device_identity: DeviceIdentity) → None` — admin only
- `peer_revoke_device(peer_id, device_id) → None` — admin only
- `peer_revoke(peer_id) → None` — admin only
- `peer_register_self() → None` — bootstrap for the first admin peer

### new models (proposed, not implemented)

```python
class DeviceIdentity(BaseModel):
    device_id: str
    public_key: str
    registered_at: datetime
    revoked_at: datetime | None = None

class PeerRecord(BaseModel):
    peer_id: str
    devices: list[DeviceIdentity]
    registered_at: datetime
    revoked_at: datetime | None = None
    role: str = "contributor"
    signature: str

class PeerIdentity(BaseModel):
    peer_id: str
    device: DeviceIdentity
```

## what this does not solve

**storage credential management.** Revoking a peer's signing key prevents future
verified writes, but does not prevent the peer from writing unverified entries or
reading shared storage. Storage credentials must be revoked out of band.

**admin key backup.** If the admin private key is lost, no new peers can be registered
or revoked.

**entry confidentiality.** Signatures provide integrity and attribution, not
confidentiality.
