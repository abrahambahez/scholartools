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
7. [Adding a second researcher](#7-adding-a-second-researcher)
8. [Adding a second device](#8-adding-a-second-device)
9. [Limitations](#9-limitations)
10. [Troubleshooting](#10-troubleshooting)

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
- `bucket` accepts an optional subdir prefix: `"MY-BUCKET/scholartools"` scopes all
  objects under `scholartools/` inside the bucket. Useful when sharing a bucket across
  multiple projects or libraries.

---

## 3. identity bootstrap

Each researcher has one keypair at `~/.config/scholartools/keys/PEER_ID/DEVICE_ID.key`.
The first researcher self-registers as admin; subsequent researchers generate a keypair
and share their public key for the admin to register.

**Required before any push or link_file call.** Also add the `peer` block to
`config.json` (the script prints it for you).

### First researcher (admin)

```bash
scht peers init sabhz laptop
scht peers register-self
```

`peers init` generates the keypair and prints JSON with the `public_key`.
`peers register-self` registers this peer as admin in the local peer directory.

Add the `peer` block to `~/.config/scholartools/config.json`:

```json
{
  "peer": {"peer_id": "sabhz", "device_id": "laptop"},
  "sync": { ... }
}
```

---

## 4. fresh setup (new library)

After steps 1–3:

```bash
scht sync push     # empty but no errors = S3 is reachable
scht sync snapshot
```

The library is empty. Start adding references normally — every write generates a change
log entry. Run `scht sync push` to upload them to S3.

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
3. Calls `create_snapshot()` to upload the full library state to S3
4. With `--upload-blobs`: calls `sync_file(citekey)` for every record that has a
   linked local file, uploading each PDF/file to `blobs/{sha256}` in S3

After migration, run push to upload any change log entries generated during the copy:

```bash
scht sync push
```

### manual migration (step by step)

If you prefer to do it manually:

```bash
# 1. copy library data
cp /old/library/dir/library.json /new/library/dir/library.json
cp -r /old/library/dir/files /new/library/dir/files
cp /old/library/dir/staging.json /new/library/dir/staging.json   # if exists
cp -r /old/library/dir/staging /new/library/dir/staging           # if exists

# 2. backfill uids
uv run python scripts/backfill_uid.py

# 3. snapshot the current state to S3
scht sync snapshot

# 4. upload blobs for all records that have a linked local file
scht sync upload-blobs

# upload-blobs sets blob_ref on each record but writes no change log entries.
# follow with snapshot to publish the updated blob_ref state to S3.
scht sync snapshot

# 5. push change log
scht sync push
```

---

## 6. verify remote state

Check that the bucket has the expected structure:

```bash
aws s3 ls s3://MY-BUCKET/changes/   --recursive | wc -l
aws s3 ls s3://MY-BUCKET/snapshots/ --recursive | wc -l
aws s3 ls s3://MY-BUCKET/blobs/     --recursive | grep -v '\.meta$' | wc -l
```

---

## 7. adding a second researcher

On the **new researcher's machine**:

1. Install scholartools and configure `config.json` with the same bucket credentials
   and their own `library_dir`. Do **not** add a `peer` block yet.

2. Generate a keypair:

   ```bash
   scht peers init alice laptop
   ```

   The output JSON contains `public_key`. Share it with the admin.

3. **Admin-side**: register the new researcher:

   ```bash
   echo '{"peer_id":"alice","device_id":"laptop","public_key":"<key from step 2>"}' | scht peers register
   scht sync push
   ```

4. New researcher: add the `peer` block to their `config.json`:

   ```json
   {"peer": {"peer_id": "alice", "device_id": "laptop"}, "sync": { ... }}
   ```

5. Copy or pull the peer directory so verification works:

   ```bash
   scp -r admin-machine:{library_dir}/peers/ {new_library_dir}/peers/
   ```

   Or pull after the admin has pushed the updated peer directory.

---

## 8. adding a second device

On the **new device**:

1. Install scholartools and configure `config.json` with the same bucket credentials
   and a **new** `library_dir`.

2. Bootstrap identities (steps 3a and 3b above), using the same `peer_id` but a
   different `device_id`:

   ```bash
   scht peers init sabhz desktop
   ```

3. Copy the peer directory from the first device so pull verification works:

   ```bash
   scp -r first-machine:{library_dir}/peers/ {new_library_dir}/peers/
   ```

   Or register the new device via the first machine:

   ```bash
   # on first device — after copying the new device's public key
   echo '{"peer_id":"sabhz","device_id":"desktop","public_key":"<key>"}' | scht peers add-device sabhz
   scht sync push
   ```

4. Restore from the latest snapshot on the new device:

   ```bash
   scht sync pull
   ```

5. Download blobs on demand via `scht files get <citekey>` or prefetch all:

   ```bash
   scht files prefetch
   ```

---

## 9. limitations

- **Large files (> 5 GB)**: boto3 single-part upload stalls. Academic PDFs (< 100 MB)
  are unaffected. Multipart support is deferred.

- **No automatic cache eviction**: orphaned blobs and deleted references accumulate in
  S3. Use S3 lifecycle policies for cleanup.

---

## 10. troubleshooting

| error | cause | fix |
|---|---|---|
| `local device keypair not found` | keypair not yet generated | run `bootstrap_identity.py --peer-id … --device-id …` |
| `caller peer not registered` | `peer` block set but `peer_register_self` not run | run `bootstrap_identity.py --role admin` |
| `caller is not an admin` | trying to register/revoke peers without admin role | have the admin perform the operation |
| `peer directory is not empty; use peer_register()` | `peer_register_self` called on non-empty peer directory | use `peer_register()` with an existing admin |
| `config.json has a 'sync' block but no 'peer' block` | `sync` added but identity not configured | add `peer` block and run bootstrap |
| `PushResult(errors=['sync not configured'])` | no `sync` block in config.json | add `sync` block with bucket + credentials |
| `PeerInitResult(error='key already exists ...')` | key already initialized | safe to ignore; key is reused |
| `ModuleNotFoundError: No module named 'boto3'` | boto3 not installed | `uv sync --extra sync` |
| S3 `NoCredentialsError` | wrong access_key / secret_key | verify IAM credentials in config.json |
| S3 `NoSuchBucket` | bucket name typo or wrong region | verify bucket name in config.json |
