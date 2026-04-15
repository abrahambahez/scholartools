# spec: 010-role-logic

## findings

`LibraryCtx` carries `admin_peer_id: str = "_admin"` and `admin_device_id: str = "_admin"` (models.py:134-135). These fields are not exclusive to admin operations — they represent the signing identity of the local machine for every peer. The misnaming causes two protocol bugs:

- `push()` in `services/sync.py` writes to `changes/_admin/{hlc}.json` for all peers, colliding filenames across researchers (sync.py:123).
- `pull()` skips entries where `parts[1] == ctx.admin_peer_id` (sync.py:175), which equals `"_admin"` for everyone, so every peer skips all entries in the bucket including those from other researchers.

`_build_ctx()` in `__init__.py` passes the hardcoded string `"_admin"` directly to `make_sync_storage()` (lines 72-73) and sets no `admin_peer_id`/`admin_device_id` on the returned `LibraryCtx` (they inherit defaults). The config (`Settings`) has no `peer` block — there is no mechanism to read per-researcher identity from config.

`DeviceIdentity.role` defaults to `"peer"` (models.py:337). The string `"peer"` is ambiguous since every entity in the system is a peer; the feat renames it to `"contributor"` while treating old `"peer"` values as equivalent at runtime.

`peer_register()` assigns `role="admin"` only when `identity.peer_id == ctx.admin_peer_id and identity.device_id == ctx.admin_device_id` (peers.py:114-116) — effectively when registering the ghost `_admin` identity. There is no real admin role check before write operations; the current "check" is a keypair-match against the `_admin` record, not against the calling peer's entry.

`bootstrap_identity.py` initializes a `_admin/_admin` ghost keypair then registers the real researcher against it. This pattern is retired by this feature.

References to `admin_peer_id` / `admin_device_id` across the codebase:

| file | lines |
|---|---|
| `scholartools/models.py` | 134, 135 |
| `scholartools/__init__.py` | 331, 334, 346, 347, 353, 378, 385, 386 |
| `scholartools/services/peers.py` | 53, 61, 62, 64, 72, 109, 115, 116, 147, 182, 218 |
| `scholartools/services/sync.py` | 46, 123, 175, 407, 412, 422, 432, 433, 462, 472, 473 |

`resolve_conflict()` and `restore_reference()` in `__init__.py` build `ChangeLogEntry` and key paths directly from `ctx.admin_peer_id`/`ctx.admin_device_id` (lines 331-386).

`docs/remote-setup.md` section 8 explicitly acknowledges the multi-researcher limitation as a known gap. Section 3 documents the now-retired two-keypair bootstrap model.

## objective

Wire per-researcher identity (`peer_id`, `device_id`) through config into `LibraryCtx`, rename the misleading `admin_peer_id`/`admin_device_id` fields to `peer_id`/`device_id`, replace the ghost `_admin/_admin` bootstrap with `peer_register_self()` for the first peer, and enforce role-based authorization (admin vs. contributor) on all peer-management write operations. After this feature, two researchers can push to the same bucket without collisions and each will correctly pull the other's entries.

## acceptance criteria

- WHEN `config.json` contains a `sync` block and no `peer` block THEN `load_settings()` MUST raise `ValueError` with a message indicating that `peer` is required when `sync` is present.
- WHEN `config.json` contains a `peer` block THEN `Settings.peer` MUST be a `PeerSettings` instance with `peer_id` and `device_id` populated, and any extra keys in the block MUST raise a validation error.
- WHEN `config.json` contains no `sync` block THEN `Settings.peer` MAY be absent without error.
- WHEN `_build_ctx()` runs with a valid `peer` block THEN the resulting `LibraryCtx.peer_id` and `LibraryCtx.device_id` MUST equal `s.peer.peer_id` and `s.peer.device_id` respectively, never the string `"_admin"`.
- WHEN `push()` is called THEN change log entries MUST be written to `changes/{peer_id}/{hlc}.json` where `peer_id` is the configured researcher handle, not `"_admin"`.
- WHEN `pull()` is called THEN only entries under `changes/{peer_id}/` matching the local peer's own `peer_id` MUST be skipped; entries from other `peer_id` prefixes MUST be applied.
- WHEN `peer_register()`, `peer_add_device()`, or `peer_revoke()` is called and the local keypair for `ctx.peer_id`/`ctx.device_id` does not exist THEN the function MUST return `Result(ok=False, error="local device keypair not found")` without touching storage.
- WHEN `peer_register()`, `peer_add_device()`, or `peer_revoke()` is called and no peer directory entry exists for `ctx.peer_id` THEN the function MUST return `Result(ok=False, error="caller peer not registered")`.
- WHEN `peer_register()`, `peer_add_device()`, or `peer_revoke()` is called and the caller's peer directory entry has `role != "admin"` THEN the function MUST return `Result(ok=False, error="caller is not an admin")`.
- WHEN a `DeviceIdentity` is created with no explicit `role` THEN `role` MUST default to `"contributor"`.
- WHEN any role check reads a `DeviceIdentity` where `role == "peer"` THEN it MUST treat it as equivalent to `"contributor"` at runtime; no migration or backfill is required.
- WHEN `peer_register_self()` is called and `peers_dir` does not exist or contains zero files THEN the function MUST create a self-signed `PeerRecord` with `role="admin"` for the caller's `(peer_id, device_id)`, write it to `{peers_dir}/{peer_id}`, and return `Result(ok=True)`.
- WHEN `peer_register_self()` is called and `peers_dir` exists and contains any file THEN the function MUST return `Result(ok=False, error="peer directory is not empty; use peer_register() with an existing admin")` without writing anything.
- WHEN `bootstrap_identity.py` is run with `--role admin` THEN it MUST call `peer_init()` followed by `peer_register_self()`, print the `peer` block for `config.json`, and exit non-zero on error.
- WHEN `bootstrap_identity.py` is run with `--role contributor` or no `--role` flag THEN it MUST call `peer_init()` only, print the `peer` block and the base64 public key for the admin to register, without calling any peer directory write function.

## tasks

- [ ] task-01: `models.py` — blocks: none
  - Add `PeerSettings(BaseModel)` with `model_config = ConfigDict(extra="forbid")`, `peer_id: str`, `device_id: str`
  - Add `Settings.peer: PeerSettings | None = None`
  - Rename `LibraryCtx.admin_peer_id` → `peer_id` and `admin_device_id` → `device_id`; change defaults to `""` (forces explicit wiring, surfaces accidental omission)
  - Change `DeviceIdentity.role` default from `"peer"` to `"contributor"`
  - Unit tests: `PeerSettings` rejects extra keys; `Settings` with and without `peer` block; `DeviceIdentity` default role is `"contributor"`

- [ ] task-02: `config.py` — blocks: task-01
  - After `Settings.model_validate(data)` in `load_settings()`, add: if `_settings.sync is not None and _settings.peer is None` raise `ValueError` with a clear message pointing the user to add the `peer` block
  - Unit tests: `load_settings()` raises `ValueError` when `sync` present and `peer` absent; passes when both present; passes when neither present

- [ ] task-03: `__init__.py` — blocks: task-01, task-02
  - In `_build_ctx()`: replace hardcoded `"_admin"` strings in `make_sync_storage()` call with `s.peer.peer_id` and `s.peer.device_id` (guard with `if s.peer`); set `peer_id=s.peer.peer_id if s.peer else ""` and `device_id=s.peer.device_id if s.peer else ""` on `LibraryCtx` constructor
  - Rename all `ctx.admin_peer_id` → `ctx.peer_id` and `ctx.admin_device_id` → `ctx.device_id` in `resolve_conflict()` and `restore_reference()`
  - Unit tests: `_build_ctx()` with a `peer` block produces `LibraryCtx` with correct `peer_id`/`device_id`

- [ ] task-04: `services/sync.py` — blocks: task-01
  - Rename all `ctx.admin_peer_id` → `ctx.peer_id` and `ctx.admin_device_id` → `ctx.device_id` (lines 46, 123, 175, 407, 412, 422, 432, 433, 462, 472, 473)
  - Verify `_load_privkey()` uses `ctx.peer_id`/`ctx.device_id`
  - Unit tests: `push()` writes entry with correct `peer_id` from ctx; `pull()` skips own prefix and processes a different `peer_id` prefix

- [ ] task-05: `services/peers.py` — blocks: task-01, task-04
  - Rename `_load_admin_key(ctx)` → `_load_caller_key(ctx)`; update to use `ctx.peer_id`/`ctx.device_id`
  - Remove `_admin_key_matches_record()` entirely
  - Add `_check_admin_role(ctx, peers_dir) -> Result` implementing the 5-step sequence: (1) load keypair, (2) load caller directory entry, (3) find device entry for `ctx.device_id`, (4) check `role == "admin"`, (5) return `Result(ok=True)`; each step returns a typed error on failure
  - Replace admin keypair check in `peer_register()`, `peer_add_device()`, `peer_revoke_device()`, `peer_revoke()` with `_check_admin_role()`
  - Update `peer_register()` to assign `role="admin"` only when `identity.peer_id == ctx.peer_id and identity.device_id == ctx.device_id` (self-registration path); otherwise `role="contributor"`
  - Unit tests: all 5 branches of `_check_admin_role`; `peer_register()` blocked when caller not admin; old `_admin_key_matches_record` pattern absent

- [ ] task-06: `services/peers.py` — blocks: task-05
  - Add `async def peer_register_self(ctx: LibraryCtx) -> Result`
  - Check `ctx.peers_dir` configured; if `peers_dir` absent or zero files: load caller keypair, derive public key, build and self-sign `PeerRecord` with `role="admin"`, write to `{peers_dir}/{ctx.peer_id}`, return `Result(ok=True)`
  - If peers_dir exists and non-empty: return `Result(ok=False, error="peer directory is not empty; use peer_register() with an existing admin")`
  - Unit tests: succeeds on empty dir, writes record with `role="admin"`; fails on non-empty dir; fails when keypair not found

- [ ] task-07: `__init__.py` — blocks: task-06
  - Add sync wrapper `def peer_register_self() -> Result`
  - Export `PeerSettings` from model imports and re-export at module level
  - Unit test: `peer_register_self` accessible from public API

- [ ] task-08: `scripts/bootstrap_identity.py` — blocks: task-07
  - Rewrite: add `--role` flag with `choices=["admin", "contributor"]`, default `"contributor"`
  - Remove all `_admin/_admin` keypair initialization
  - Both roles: call `peer_init()`; handle key-already-exists gracefully; print `peer` block for `config.json`
  - `--role admin`: also call `st.peer_register_self()`; print confirmation; exit non-zero on error
  - `--role contributor`: print base64 public key with instruction to share with admin; no directory writes

- [ ] task-09: `docs/remote-setup.md` — blocks: task-08
  - Section 3: collapse to single `bootstrap_identity.py --role admin` command; remove manual step-3a/3b/3c
  - Add new section "Adding a second researcher" covering `--role contributor` flow and admin-side `peer_register()` step
  - Section 8: remove multi-researcher limitation bullet (fixed by this feat)
  - Troubleshooting: replace `_admin` keypair entries with new error messages from task-05

- [ ] task-10: full unit test pass (`tests/unit/test_peers.py` + regression suite) — blocks: task-05, task-06
  - Role check sequence all 5 branches
  - `peer_register_self()` on empty dir, non-empty dir, missing keypair
  - `peer_register()`, `peer_add_device()`, `peer_revoke()` blocked when caller is not admin
  - `DeviceIdentity.role` default is `"contributor"`
  - Old `"peer"` role value rejected by `_check_admin_role` (predicate `role != "admin"` covers it — add explicit test)

- [ ] task-11: `tests/integration/test_role_lifecycle.py` — blocks: task-10
  - peer-A: `peer_register_self()` → admin
  - peer-B: `peer_init()` only (contributor)
  - peer-A: `peer_register(peer-B identity)` with role `contributor`
  - peer-A: push 2 entries to `changes/peer-A/`
  - peer-B: push 1 entry to `changes/peer-B/`
  - peer-A: pull → applies peer-B's entry
  - peer-B: `peer_register()` → `"caller is not an admin"` error
  - `@pytest.mark.integration`; local tmp dir as shared backend

- [ ] task-12: `feature_list.json` — blocks: none
  - Append `{"id": "role-logic", "title": "Role logic — per-peer identity in config, admin/contributor roles, peer_register_self bootstrap", "spec": "docs/specs/010-role-logic.md", "passes": false}`

- [ ] task-13: full suite green + ruff clean — blocks: task-11
  - `uv run pytest` — no regressions on 399+ existing tests
  - `uv run ruff check .` — zero errors

## risks

1. **Blast radius of field rename.** `admin_peer_id` and `admin_device_id` appear in 4 files across 30+ lines. A missed reference compiles but produces silent protocol bugs (wrong signing path, wrong S3 prefix). The findings table enumerates every occurrence; implementer must grep again after rename to confirm zero residuals.

2. **`make_sync_storage` signature.** `_build_ctx()` passes `peer_id` and `device_id` as positional args to `make_sync_storage()`. The composite adapter stores these values and passes them into `ChangeLogEntry` construction — those paths must also use config values, not cached `"_admin"` strings.

3. **Breaking config change.** Any `config.json` with `sync` but no `peer` will raise `ValueError` on next startup. Users must add the `peer` block before upgrading. The bootstrap script and updated `remote-setup.md` are the migration path.

4. **Existing `_admin` peer directory records.** Deployments where the ghost `_admin` identity was registered with `role="admin"` continue to work if the admin re-runs `bootstrap_identity.py --role admin` (which calls `peer_register_self()` — will fail if peers_dir is non-empty, so the admin must manually update their `config.json` `peer` block to match the actual `peer_id` they want to use and call `peer_register()` themselves). Document in `remote-setup.md` migration notes.

5. **`peer_register_self()` non-atomicity.** Empty-directory check and write are not atomic on a shared filesystem. In the standard deployment `peers/` is local, so this is theoretical. Document as a caveat.
