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

Changes take effect on the next `scht` command.

---

## 3. Initialize this device's identity

Run once per device. Generates an Ed25519 keypair so your changes can be signed and verified.

```sh
scht peers init alice laptop
# prints PeerIdentity JSON: {peer_id, device_id, public_key}

scht peers register-self
# Writes your public key into the local peers registry.
```

`peer_id` and `device_id` must match what you put in config.json.

---

## 4. Upload the first snapshot

Uploads a full copy of your library to the bucket. Other devices will bootstrap from this.

```sh
scht sync snapshot
```

Run once after initial setup, and again after major bulk imports.

---

## 5. Daily sync workflow

Always pull before pushing to apply any remote changes first.

```sh
scht sync pull    # apply remote changes
# ... make local edits (add/update/delete references) ...
scht sync push    # upload your change log entries to the bucket
```

After pulling, check for conflicts:

```sh
scht sync list-conflicts
# prints ConflictRecord list: uid, field, local_value, local_timestamp_hlc,
#                             remote_value, remote_timestamp_hlc, remote_peer_id

# Pick a winner for each conflict:
scht sync resolve-conflict <uid> <field> <local_value>    # keep local
scht sync resolve-conflict <uid> <field> <remote_value>   # keep remote
```

To recover a reference deleted by a remote peer:

```sh
scht sync restore <citekey>
```

---

## 6. Add a second device (same researcher)

Use this to sync `alice`'s library to a new machine (e.g. `"desktop"`).

**On the new device:**

1. Edit config.json — same `peer_id`, new `device_id`:
   ```json
   { "peer": { "peer_id": "alice", "device_id": "desktop" } }
   ```
2. Generate a keypair and share the identity JSON with the first device:
   ```sh
   scht peers init alice desktop
   # copy the printed identity JSON
   ```

**On the first device (as admin):**

```sh
scht peers add-device alice '<identity-json>'
# or: echo '<identity-json>' | scht peers add-device alice
scht sync push    # publish the updated peer record to the bucket
```

**Back on the new device:**

```sh
scht peers register-self
scht sync pull    # bootstraps library from the snapshot + change log
```

---

## 7. Add a collaborator (different researcher)

Use this to give a different person (`"bob"`) access to the shared bucket.

**Bob, on his device:**

```sh
scht peers init bob bob-laptop
# copy the printed identity JSON
scht peers register-self
```

**Alice (admin), on her device:**

```sh
scht peers register '<bob-identity-json>'
# or: echo '<bob-identity-json>' | scht peers register
scht sync push    # publishes bob's peer record to the bucket
```

**Bob:**

```sh
scht sync pull    # bootstraps from the shared library
```

---

## 8. Revoke access

Revoke a single device (e.g. a lost laptop):

```sh
scht peers revoke-device alice laptop
scht sync push
```

Revoke an entire peer (removes all their devices):

```sh
scht peers revoke bob
scht sync push
```

Revoked devices are rejected at pull time on all other peers.

---

## CLI reference

```sh
# Identity
scht peers init <peer_id> <device_id>
scht peers register-self
scht peers register [<identity_json>|-]
scht peers add-device <peer_id> [<identity_json>|-]
scht peers revoke-device <peer_id> <device_id>
scht peers revoke <peer_id>

# Sync
scht sync push
scht sync pull
scht sync snapshot
scht sync list-conflicts
scht sync resolve-conflict <uid> <field> <value>
scht sync restore <citekey>
```
