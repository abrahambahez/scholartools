---
name: scholartools-sync-peers
description: scholartools distributed sync and peer management — step-by-step setup guide for S3-backed sync, adding devices and collaborators, daily sync workflow, conflict resolution, and peer lifecycle management. Use this whenever the user asks about syncing their scholartools library across devices, setting up a new device or collaborator, registering or revoking peers, handling sync conflicts, or any task involving the S3-backed change log. Guide the user through the full journey even if they only mention one step.
---

Sync works by writing a cryptographically signed change log to an S3-compatible bucket. Every device reads each other's changes and verifies signatures — no central server, no trust required.

## Journey overview

1. [Get a bucket](#1-get-a-bucket)
2. [Configure this device](#2-configure-this-device)
3. [Initialize this device's identity](#3-initialize-this-devices-identity)
4. [Upload the first snapshot](#4-upload-the-first-snapshot)
5. [Daily sync workflow](#5-daily-sync-workflow)
6. [Add a second device (same researcher)](#6-add-a-second-device-same-researcher)
7. [Add a collaborator (different researcher)](#7-add-a-collaborator-different-researcher)
8. [Revoke access](#8-revoke-access)

---

## 1. Get a bucket

You need an S3-compatible object storage bucket. Any of these work:

| Provider | Notes |
|----------|-------|
| **AWS S3** | Standard. Set `endpoint` to `null`. |
| **Cloudflare R2** | No egress fees. Set `endpoint` to your R2 endpoint URL. |
| **Backblaze B2** | Cheap. Set `endpoint` to the B2 S3-compatible URL. |
| **MinIO** | Self-hosted. Set `endpoint` to your MinIO URL. |

From your provider, collect: **bucket name**, **access key**, **secret key**, and **endpoint URL** (null for AWS).

---

## 2. Configure this device

Edit `~/.config/scholartools/config.json` (Windows: `C:\Users\<user>\.config\scholartools\config.json`).

Add a `sync` block and a `peer` block. Choose any names for `peer_id` (who you are, e.g. `"alice"`) and `device_id` (this machine, e.g. `"laptop"`):

```json
{
  "sync": {
    "bucket": "my-scholartools-bucket",
    "access_key": "YOUR_ACCESS_KEY",
    "secret_key": "YOUR_SECRET_KEY",
    "endpoint": null
  },
  "peer": {
    "peer_id": "alice",
    "device_id": "laptop"
  }
}
```

Then reload:

```python
reset()
```

---

## 3. Initialize this device's identity

Run once per device. This generates an Ed25519 keypair so your changes can be signed and verified by other devices.

```python
result = peer_init("alice", "laptop")
# result.identity -> PeerIdentity(peer_id, device_id, public_key)

peer_register_self()
# Writes your public key into the local peers registry.
```

`peer_id` and `device_id` must match what you put in config.json.

---

## 4. Upload the first snapshot

Uploads a full copy of your library to the bucket. Other devices will bootstrap from this.

```python
create_snapshot()
```

Run this once after the initial setup, and again after major bulk imports.

---

## 5. Daily sync workflow

Always pull before pushing to apply any remote changes first.

```python
pull()   # apply remote changes; returns applied_count, rejected_count, conflicted_count
# ... make local edits (add/update/delete references) ...
push()   # upload your change log entries to the bucket
```

After pulling, check for conflicts:

```python
conflicts = list_conflicts()
# ConflictRecord: uid, field, local_value, local_timestamp_hlc,
#                 remote_value, remote_timestamp_hlc, remote_peer_id

for c in conflicts:
    # Inspect c.local_value vs c.remote_value, pick the winner:
    resolve_conflict(c.uid, c.field, c.local_value)   # keep local
    # or
    resolve_conflict(c.uid, c.field, c.remote_value)  # keep remote
```

To recover a reference deleted by a remote peer:

```python
restore_reference(citekey)
```

---

## 6. Add a second device (same researcher)

Use this when you want to sync `alice`'s library to a new machine (e.g. `"desktop"`).

**On the new device:**

1. Edit config.json — same `peer_id`, new `device_id`:
   ```json
   { "peer": { "peer_id": "alice", "device_id": "desktop" } }
   ```
2. Generate a keypair for this device:
   ```python
   result = peer_init("alice", "desktop")
   identity = result.identity   # share this with the first device
   ```

**On the first device (as admin):**

```python
peer_add_device("alice", identity)
# identity is the PeerIdentity from the new device: {peer_id, device_id, public_key}
push()   # publish the updated peer record to the bucket
```

**Back on the new device:**

```python
peer_register_self()
pull()   # bootstraps library from the snapshot + change log
```

---

## 7. Add a collaborator (different researcher)

Use this to give a different person (`"bob"`) access to the shared bucket.

**Bob, on his device:**

```python
result = peer_init("bob", "bob-laptop")
identity = result.identity   # share this with alice
peer_register_self()
```

**Alice (admin), on her device:**

```python
peer_register(identity)    # registers bob's device locally
push()                     # publishes bob's peer record to the bucket
```

**Bob:**

```python
pull()   # bootstraps from the shared library
```

Devices are `"contributor"` role by default. To make Bob an admin, set `role="admin"` in the `DeviceIdentity` passed to `peer_add_device`.

---

## 8. Revoke access

Revoke a single device (e.g. a lost laptop):

```python
peer_revoke_device("alice", "laptop")
push()
```

Revoke an entire peer (removes all their devices):

```python
peer_revoke("bob")
push()
```

Revoked devices are rejected at pull time on all other peers.

---

## API reference

```python
# Identity
peer_init(peer_id: str, device_id: str) -> PeerInitResult
peer_register_self() -> Result
peer_register(identity: PeerIdentity) -> PeerRegisterResult
peer_add_device(peer_id: str, device_identity: PeerIdentity) -> PeerAddDeviceResult
peer_revoke_device(peer_id: str, device_id: str) -> PeerRevokeDeviceResult
peer_revoke(peer_id: str) -> PeerRevokeResult

# Sync
push() -> PushResult              # entries_pushed: int, errors: list[str]
pull() -> PullResult              # applied_count, rejected_count, conflicted_count, errors
create_snapshot() -> None

# Conflicts
list_conflicts() -> list[ConflictRecord]
resolve_conflict(uid: str, field: str, winning_value) -> Result
restore_reference(citekey: str) -> Result
```
