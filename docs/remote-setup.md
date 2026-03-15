# remote-setup.md — end-to-end remote sync setup

## overview

scholartools sync uses an S3-compatible bucket as a shared backbone. The bucket holds
three namespaces: `changes/` (append-only change log), `snapshots/` (full library
dumps), and `blobs/` (content-addressed file storage for PDFs and other linked files).

All writes are signed with an Ed25519 keypair that lives locally — credentials never
enter the bucket. The bucket stores public-key-verifiable records only.

This guide covers:
1. [AWS prerequisites](#1-aws-prerequisites)
2. [config.json](#2-configjson)
3. [Identity bootstrap](#3-identity-bootstrap) ← **required before any push/pull**
4. [Fresh setup](#4-fresh-setup-new-library)
5. [Migration from an existing library](#5-migration-from-an-existing-library)
6. [Verify remote state](#6-verify-remote-state)
7. [Adding a second device](#7-adding-a-second-device)
8. [Limitations](#8-limitations)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. AWS prerequisites

### Create the S3 bucket

In the AWS console (or CLI):

```bash
aws s3api create-bucket \
  --bucket MY-BUCKET \
  --region us-east-1
```

Settings that matter:
- Block public access: **ON** (default, keep it)
- Versioning: OFF (change log is already append-only)
- Server-side encryption: optional but recommended (AES-256 or KMS)

### Create an IAM user with a scoped policy

Create a programmatic-access IAM user and attach this inline policy
(replace `MY-BUCKET` with your bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject",
      "s3:HeadObject",
      "s3:ListBucket",
      "s3:DeleteObject"
    ],
    "Resource": [
      "arn:aws:s3:::MY-BUCKET",
      "arn:aws:s3:::MY-BUCKET/*"
    ]
  }]
}
```

Save the **Access Key ID** and **Secret Access Key** — they appear only once.

---

## 2. config.json

Location: `~/.config/scholartools/config.json`

Minimal working config:

```json
{
  "backend": "local",
  "local": {
    "library_dir": "/absolute/path/to/your/library/dir"
  },
  "apis": {
    "email": "you@example.com",
    "sources": []
  },
  "llm": {},
  "sync": {
    "bucket": "MY-BUCKET",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  }
}
```

Notes:
- `endpoint` is omitted for real AWS. Set it only for MinIO or other S3-compatible
  services (e.g. `"endpoint": "http://localhost:9000"`).
- `library_dir` must be an absolute path. All other local paths (`library.json`,
  `files/`, `staging.json`, `peers/`) are computed under it automatically.
- The `sync` block activates the composite storage adapter that writes a change log
  entry on every library write.

---

## 3. identity bootstrap

scholartools uses two distinct keypairs:

| keypair | path | purpose |
|---|---|---|
| `_admin/_admin` | `~/.config/scholartools/keys/_admin/_admin.key` | signs all push entries and peer records |
| `PEER_ID/DEVICE_ID` | `~/.config/scholartools/keys/PEER_ID/DEVICE_ID.key` | your identity in the peer directory |

**Both must be created before any push or link_file call.** The `_admin` keypair is the
local signing authority. Your personal peer keypair is your identity registered in the
shared peer directory so other devices/peers can verify your signatures during pull.

### step 3a — initialize the admin signing keypair

```python
import scholartools as st

admin = st.peer_init("_admin", "_admin")
print(admin)
# PeerInitResult(identity=PeerIdentity(peer_id='_admin', device_id='_admin', public_key='...'))
```

Key written to: `~/.config/scholartools/keys/_admin/_admin.key` (mode 0600).

### step 3b — initialize your personal peer keypair

```python
result = st.peer_init("YOUR_PEER_ID", "YOUR_DEVICE_ID")
print(result)
# PeerInitResult(identity=PeerIdentity(peer_id='yourname', device_id='laptop', public_key='...'))
```

Pick stable, readable identifiers:
- `peer_id`: your researcher handle (e.g. `"sabhz"`)
- `device_id`: the machine (e.g. `"laptop"`, `"desktop"`)

### step 3c — register your peer identity

```python
from scholartools import PeerIdentity

identity = PeerIdentity(
    peer_id="YOUR_PEER_ID",
    device_id="YOUR_DEVICE_ID",
    public_key=result.identity.public_key,
)
reg = st.peer_register(identity)
print(reg)
# PeerRegisterResult(peer_id='yourname')
```

This writes a signed peer record to `{library_dir}/peers/YOUR_PEER_ID`.

### automated: `scripts/bootstrap_identity.py`

```bash
uv run python scripts/bootstrap_identity.py --peer-id sabhz --device-id laptop
```

---

## 4. fresh setup (new library)

After steps 1–3:

```python
import scholartools as st

# verify config loaded and sync reachable
result = st.push()
print(result)
# PushResult(entries_pushed=0, errors=[])   ← empty but no errors = S3 is reachable

st.create_snapshot()
```

The library is empty. Start adding references normally — every write generates a change
log entry. Call `st.push()` to upload them to S3.

---

## 5. migration from an existing library

Use the migration script to copy an existing library into the new directory and upload
all blobs:

```bash
uv run python scripts/migrate_library.py \
  --from-dir /old/library/dir \
  --upload-blobs
```

What the script does:
1. Copies `library.json` from `--from-dir` to the configured `library_dir`
2. Copies `files/` from `--from-dir` to `library_dir/files/`
3. Runs `backfill_uid.py` to ensure all records have `uid` set
4. Calls `create_snapshot()` to upload the full library state to S3
5. With `--upload-blobs`: calls `link_file(citekey, path)` for every record that has a
   linked local file, uploading each PDF/file to `blobs/{sha256}` in S3

After migration, run `push()` to upload any change log entries generated during the
copy:

```python
import scholartools as st
result = st.push()
print(result)
```

### manual migration (step by step)

If you prefer to do it manually:

```bash
# 1. copy library data
cp /old/library/dir/library.json /new/library/dir/library.json
cp -r /old/library/dir/files /new/library/dir/files

# 2. reload scholartools so it sees the new data
```

```python
import scholartools as st

# 3. backfill uids
# (run from shell: uv run python scripts/backfill_uid.py)

# 4. snapshot the current state to S3
st.create_snapshot()

# 5. upload blobs for all records that have a linked file
result = st.list_references()
for row in result.references:
    rec = st.get_reference(row.citekey).reference
    if rec and rec.file_record:
        r = st.link_file(row.citekey, rec.file_record.path)
        if not r.ok:
            print(f"  {row.citekey}: {r.error}")

# 6. push change log
st.push()
```

---

## 6. verify remote state

Check that the bucket has the expected structure:

```python
from scholartools.adapters import s3_sync
from scholartools.config import load_settings

cfg = load_settings().sync

changes = s3_sync.list_keys(cfg, "changes/")
snapshots = s3_sync.list_keys(cfg, "snapshots/")
blobs = [k for k in s3_sync.list_keys(cfg, "blobs/") if not k.endswith(".meta")]

print(f"changes:   {len(changes)}")
print(f"snapshots: {len(snapshots)}")
print(f"blobs:     {len(blobs)}")
```

---

## 7. adding a second device

On the **new device**:

1. Install scholartools and configure `config.json` with the same bucket credentials
   and a **new** `library_dir`.

2. Bootstrap identities (steps 3a and 3b above), using the same `peer_id` but a
   different `device_id`:

   ```bash
   uv run python scripts/bootstrap_identity.py --peer-id sabhz --device-id desktop
   ```

3. Copy the peer directory from the first device so pull verification works:

   ```bash
   scp -r first-machine:{library_dir}/peers/ {new_library_dir}/peers/
   ```

   Or register the new device via the first machine:

   ```python
   # on first device — after copying the new device's public key
   from scholartools import PeerIdentity
   st.peer_add_device("sabhz", PeerIdentity(
       peer_id="sabhz",
       device_id="desktop",
       public_key="<public_key from step 3b on new device>",
   ))
   st.push()
   ```

4. Restore from the latest snapshot on the new device:

   ```python
   from scholartools.adapters import s3_sync
   from scholartools.config import load_settings
   import json, shutil

   cfg = load_settings().sync
   snapshots = sorted(s3_sync.list_keys(cfg, "snapshots/"))
   latest = snapshots[-1]

   import tempfile
   from pathlib import Path
   with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
       tmp = Path(f.name)
   s3_sync.download(cfg, latest, tmp)
   data = json.loads(tmp.read_text())
   tmp.unlink()

   from scholartools.config import load_settings
   lib_file = load_settings().local.library_file
   lib_file.write_text(json.dumps(data["library"], ensure_ascii=False))
   print(f"restored {len(data['library'])} records from {latest}")
   ```

5. Download blobs on demand via `st.get_file(citekey)` or prefetch all:

   ```python
   result = st.prefetch_blobs()
   print(result)
   ```

---

## 8. limitations

- **Multi-researcher sync (different `peer_id` per researcher) is not yet fully wired.**
  The current `_build_ctx()` hardcodes the signing identity as `_admin/_admin` for all
  peers. Two researchers pushing to the same bucket would collide under the same
  `changes/_admin/` prefix and neither would pull the other's entries (pull skips own
  `peer_id`). Multi-researcher support requires configuring `admin_peer_id` and
  `admin_device_id` per researcher in `config.json` — tracked as a future improvement.

- **Large files (> 5 GB)**: boto3 single-part upload stalls. Academic PDFs (< 100 MB)
  are unaffected. Multipart support is deferred.

- **No automatic cache eviction**: orphaned blobs and deleted references accumulate in
  S3. Use S3 lifecycle policies for cleanup.

---

## 9. troubleshooting

| error | cause | fix |
|---|---|---|
| `admin keypair not found` | `_admin/_admin.key` missing | run `peer_init("_admin", "_admin")` first |
| `local device keypair not found` (in push) | same as above | same fix |
| `PushResult(errors=['sync not configured'])` | no `sync` block in config.json | add `sync` block with bucket + credentials |
| `PeerInitResult(error='key already exists ...')` | key already initialized | safe to ignore; key is reused |
| `PeerRegisterResult(error='admin keypair does not match ...')` | key file replaced after initial register | delete `{peers_dir}/_admin` and re-register |
| S3 `NoCredentialsError` | wrong access_key / secret_key | verify IAM credentials in config.json |
| S3 `NoSuchBucket` | bucket name typo or wrong region | verify bucket name in config.json |
