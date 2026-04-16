# feat 010: role logic — per-peer identity in config and admin/contributor roles

version: 0.2
status: deprecated

> **Deprecated (v0.13.0, spec 027):** Role logic was removed from core together with peer management (feat 007) and distributed sync (feat 008). The `peer` config block, `PeerSettings` model, `peer_id`/`device_id` fields on `LibraryCtx`, and all role-check logic were deleted. This will be re-introduced as part of a future `loretools-sync` plugin. This document is preserved as the design reference for that future work.

---

## context

Feats 007 and 008 built the signing infrastructure and the change log protocol. Both
worked correctly in isolation, but `_build_ctx()` hardcoded `admin_peer_id="_admin"` and
`admin_device_id="_admin"` as the signing identity for every peer on every machine.

This broke multi-peer sync: every peer pushed to `changes/_admin/{hlc}.json` and pull
skipped all entries where `peer_id == ctx.admin_peer_id` — which was `"_admin"` for
everyone — so every peer skipped every entry in the bucket.

This feat closed that gap by introducing `peer_id` and `device_id` as first-class config
fields, and formalizing two roles — **admin** and **contributor**.

## proposed design

### `config.json` — `peer` block

```json
{
  "peer": {
    "peer_id": "sabhz",
    "device_id": "laptop"
  }
}
```

`peer_id` and `device_id` are required when a `sync` block is present.

### `PeerSettings` model (proposed)

```python
class PeerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    peer_id: str
    device_id: str
```

### roles

| role | can push own changes | can pull and verify | can register / revoke peers |
|---|---|---|---|
| `admin` | yes | yes | yes |
| `contributor` | yes | yes | no |

Role lives in the peer directory entry — not in `config.json`. This prevents self-promotion.

### `peer_register_self()`

Bootstrap function for the first peer on a fresh deployment. Valid only when the peer
directory contains no files. Self-signs a peer record with `role="admin"`.

### bootstrap sequence

```bash
# first peer on a new deployment (admin)
uv run python scripts/bootstrap_identity.py \
  --peer-id sabhz --device-id laptop --role admin

# adding a second researcher (contributor)
uv run python scripts/bootstrap_identity.py \
  --peer-id elena --device-id desktop --role contributor
```

## design decisions

**Role in peer directory, not in config.** The peer directory is the trust anchor —
signed by the admin and shared across peers via the bucket.

**`peer_register_self()` instead of `_admin` bootstrap.** Self-registration on an empty
directory is the honest primitive: the first peer declares themselves admin with no prior
authority.

**Print, don't write `config.json`.** The bootstrap script prints the `peer` block
rather than mutating `config.json` silently.
