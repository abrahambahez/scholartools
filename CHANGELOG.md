# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.1] - 2026-03-23

### Added
- Landing page (`site/`) with hero, research workflow, envisioned features, and vision sections

## [0.12.0] - 2026-03-21

### Changed
- `push()` and `pull()` renamed to `push_changelog()` and `pull_changelog()` in the public API, service layer, and CLI (`scht sync push-changelog`, `scht sync pull-changelog`) to clarify that only the change log is transferred, not file blobs

## [0.11.0] - 2026-03-20

### Added
- `attach_file(citekey, path)` — copies file to `files/` and registers filename-only path; no S3 side effects
- `detach_file(citekey)` — deletes local copy and clears `_file`; blocked if `blob_ref` is set
- `sync_file(citekey)` — uploads attached file to S3, writes `link_file` change log entry, sets `blob_ref`
- `unsync_file(citekey)` — clears `blob_ref` and writes `unlink_file` change log entry; leaves local file intact
- `reindex_files()` → `ReindexResult(repaired, already_ok, not_found)` — repairs stale absolute `_file.path` values after a library folder move
- CLI commands `scht files attach`, `scht files detach`, `scht files reindex`, `scht sync sync-file`, `scht sync unsync-file`
- Blob cache files now include the original extension (`{sha256}.pdf`) — fetched from `.meta` sidecar on download; legacy no-extension cache files are evicted and re-downloaded on next access

### Changed
- `FileRecord.path` now stores only the filename (`graeber2017.pdf`), never a full path — `files/` is always `library_dir/files/`; existing absolute paths are resolved via fallback logic in `get_file` and `list_files`

### Removed
- `link_file` and `unlink_file` removed from public API, service modules, and CLI — replaced by the four explicit functions above

## [0.10.0] - 2026-03-19

### Added
- PyInstaller standalone distribution bundles for macOS arm64, Linux x86_64, and Windows x86_64 — triggered by `v*` tags via GitHub Actions matrix build
- `install.sh` and `install.ps1` standalone install scripts published as separate release assets — download the correct platform zip, set PATH, and create an initial `config.json` via interactive prompts
- `scht --version` reports the version string stamped from `pyproject.toml` at build time
- Agent skill reference cards in `skills/en/` and `skills/es/` (config, references, sync-peers, files)

### Changed
- README config section expanded to a fully annotated `config.json` covering all blocks (local, apis, llm, citekey, peer, sync) with inline comments on optional fields and defaults

### Removed
- MCP server (`scht-mcp`), `mcp` optional dependency group, `.mcpb` bundle artifacts, and `docs/manuals/claude-desktop-setup.md` — MCP integration produced a brittle test surface with no viable researcher workflow; the CLI (`scht`) remains the primary interface

## [0.9.1] - 2026-03-19

### Changed
- Replaced `boto3`/`botocore` with `minio>=7.0.0` in the `sync` optional dependency group — reduces sync extra weight from ~15 MB to ~500 KB (ADR-005)
- S3 adapter (`adapters/s3_sync.py`) rewritten to use MinIO SDK; all 6 operations mapped to direct equivalents

### Fixed
- 8 unit test failures that occurred when `boto3` was not installed are now resolved

## [0.9.0] - 2026-03-18

### Added
- MCP server (`scht-mcp`) — 7 tools exposing the full research workflow to Claude Desktop and any MCP-compatible client: `discover`, `fetch`, `ingest_file`, `staging`, `library`, `manage_reference`, `files`
- `mcp>=1.0` optional dependency group; `scht-mcp` entry point registered in `pyproject.toml`
- `.mcpb` bundle support — `manifest.json` and `.mcpbignore` for `mcpb pack . dist/scholartools.mcpb`
- `docs/manuals/claude-desktop-setup.md` — user-facing install guide and opinionated workflow manual covering all five research phases

## [0.8.4] - 2026-03-16

### Fixed
- Strip redundant `error` field from CLI JSON `data` envelope

### Changed
- Updated README install instructions to use `uv sync` and `uv tool install`

## [0.8.1] - 2026-03-16

### Fixed
- Eliminated all 28 pre-existing ruff errors: F821 missing import, F401 re-export syntax,
  F841 dead assignments, E741 ambiguous variable name, E501 long lines across source and test files

## [0.8.0] - 2026-03-16

### Added
- `scht` CLI — full command-line interface covering every public API function:
  `refs`, `files`, `staging`, `discover`, `fetch`, `extract`, `sync`, `peers` subcommand groups
- All commands output JSON envelopes `{"ok": bool, "data": ..., "error": ...}` for agent consumption
- `scht` entry point registered in `pyproject.toml`

## [0.7.1] - 2026-03-16

### Fixed
- `link_file` local-only path now copies the file to `files_dir` and sets `file_record`; previously only `blob_ref` was computed, leaving local files unreachable
- `unlink_file` now deletes from `files_dir` and clears `file_record` unconditionally; `blob_ref` cleanup remains sync-only
- `get_file` falls back to `file_record.path` when `sync_config` is absent or `blob_ref` is not set

## [0.7.0] - 2026-03-16

### Added
- `peer_register_self` — bootstraps admin identity on an empty peer directory without requiring an existing admin keypair
- `PeerSettings` model exported from public API
- `scripts/bootstrap_identity.py` — `--role admin` calls `peer_register_self`; `--role contributor` prints public key for out-of-band registration

### Changed
- `LibraryCtx.admin_peer_id` / `admin_device_id` renamed to `peer_id` / `device_id`; populated from `config.json` `peer` block
- `config.json` now requires a `peer` block when `sync` is configured; `load_settings()` raises `ValueError` if absent
- `DeviceIdentity.role` default changed from `"peer"` to `"contributor"`; `peer_register` assigns `"contributor"` to non-self entries
- `peer_revoke_device`, `peer_revoke`, `peer_register`, `peer_add_device` now verify caller has `"admin"` role in peer directory

## [0.6.1] - 2026-03-14

### Fixed
- `docs/feats/007-peer-mamagement` (typo, no extension) renamed to `docs/feats/007-peer-management.md` and tracked in version control

## [0.6.0] - 2026-03-14

### Added
- Peer identity and device management: `peer_init`, `peer_register`, `peer_add_device`, `peer_revoke_device`, `peer_revoke`
- Ed25519 keypair generation via `cryptography>=42.0`; private keys stored at `~/.config/scholartools/keys/{peer_id}/{device_id}.key` (mode 0600)
- `verify_entry` — synchronous signature verification against the peer directory
- `make_pull_verifier` — factory returning a pull-time verifier that writes rejected entries to `rejected/`
- Distributed sync phase 1: `push`, `pull`, `create_snapshot`, `list_conflicts`, `resolve_conflict`, `restore_reference`
- `services/hlc.py` — HLC timestamps with per-process counter; format `{iso_utc}-{counter:04d}-{peer_id}`
- `adapters/s3_sync.py` — S3-compatible remote backend (boto3, optional import)
- `adapters/sync_composite.py` — `SyncCompositeAdapter` wrapping local store with append-only change log
- `adapters/conflicts_store.py` — file-based `ConflictRecord` persistence under `{data_dir}/conflicts/`
- New models: `DeviceIdentity`, `PeerRecord`, `PeerIdentity`, `ChangeLogEntry`, `ConflictRecord`, `PushResult`, `PullResult`, `SyncConfig`
- Optional `sync` block in `config.json` selects `SyncCompositeAdapter`; omitting it leaves local-only behaviour unchanged

### Changed
- `LibraryCtx` extended with `peers_dir`, `data_dir`, `admin_peer_id`, `admin_device_id`, `sync_config`
- `_field_timestamps` added to `Reference` for per-field LWW tracking

## [0.5.1] - 2026-03-11

### Added
- `uid` field on `ReferenceRow` — exposed in list/filter results
- `get_reference(uid=...)` — lookup by uid in addition to citekey; exactly one argument required

## [0.5.0] - 2026-03-11

### Added
- `services/uid.py` — `compute_uid()` with tier-1 cascade (DOI → arXiv → ISBN) returning `authoritative` confidence, tier-2 semantic hash from canonical fields returning `semantic` confidence
- `uid` and `uid_confidence` fields on `Reference` model
- `stage_reference()` now computes and writes uid at intake; never recomputes if already present
- `merge()` gates `semantic` confidence records unless `allow_semantic=True` is passed
- `merge()` strips container-type DOIs (chapter, entry, paper-conference) that match a library book record and recomputes uid, adding a warning
- `scripts/backfill_uid.py` — idempotent backfill script with `--dry-run`, `--verbose`, `--force` flags

### Changed
- `is_duplicate()` rewired to uid-only matching; normalized-title and ISBN logic removed
- ISBN excluded from tier-1 uid for container types (chapter, entry-encyclopedia, entry-dictionary, paper-conference) — they resolve to tier-2 semantic hash

## [0.4.1] - 2026-03-11

### Changed
- `email` moved from per-source `SourceConfig` to a single `apis.email` field in config; applies to all polite-pool sources (Crossref, OpenAlex)

## [0.4.0] - 2026-03-11

### Added
- OpenAlex adapter — free, no API key required, strong Global South coverage
- DOAJ adapter — open access journals worldwide
- Retry strategy for all search adapters: up to 3 attempts with 5s delay on 429/5xx responses

### Removed
- Latindex adapter — API is restricted and never returned results; ISSN fetch falls through to Crossref
- SciELO adapter — blocked all programmatic access (403)

### Fixed
- Crossref `_normalize` now strips `None` values from `date-parts` to prevent validation errors on undated records
- Semantic Scholar API key wired from `SEMANTIC_SCHOLAR_API_KEY` environment variable

## [0.3.0] - 2026-03-10

### Added
- `CitekeySettings` — configurable citekey generation via `config.json`: `pattern` (token template), `separator`, `etal`, `disambiguation_suffix` (`"letters"` or `"title[1-9]"`)
- Title-word disambiguation strategy with stop-word filtering (articles in 10 languages)
- All fields validated at config load time with export-safe character constraints

## [0.2.1] - 2026-03-10

### Added
- `filter_references` — local library search with five optional predicates: `query` (title substring), `author` (family/literal substring), `year` (exact), `ref_type` (exact CSL type), `has_file` (bool); `staging=True` routes to staging store
- `scholartools-test` CLI command — launches interactive Python shell with all public functions pre-imported

### Changed
- `search_references` renamed to `discover_references` to clarify it queries external APIs, not the local library

## [0.2.0] - 2026-03-09

### Added
- Staging workflow: `stage_reference`, `list_staged`, `delete_staged`, `merge` in public API
- Merge service with normalization, deduplication, validation, and file archival
- Duplicate detection service
- Storage adapter and models extended for staging (`staging.json`, `staging/` dir)
- E2E integration tests for staging and merge pipeline
- Behavioral tests for API key env var wiring into `LibraryCtx`

### Changed
- Config simplified to single global path (`~/.config/scholartools/config.json`)
- API keys moved out of config file — env-only (`ANTHROPIC_API_KEY`, `GBOOKS_API_KEY`)
- Config validation now rejects incomplete files with actionable error message
- Services without required keys are disabled gracefully rather than erroring
- Source directory flattened from `src/scholartools/` to `scholartools/`
- Models consolidated into `models.py`

## [0.1.0] - 2026-03-09

### Added
- Initial release: core library, CRUD, search, fetch, file archive, PDF extraction
- Hexagonal architecture with ports & adapters
- Pydantic v2 models, async services, sync public API wrappers
- Search sources: Crossref, Semantic Scholar, arXiv, Latindex, Google Books
- PDF extraction via pdfplumber with Claude vision fallback
- Local JSON backend

[Unreleased]: https://github.com/abrahambahez/scholartools/compare/v0.7.1...HEAD
[0.7.1]: https://github.com/abrahambahez/scholartools/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/abrahambahez/scholartools/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/abrahambahez/scholartools/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/abrahambahez/scholartools/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/abrahambahez/scholartools/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/abrahambahez/scholartools/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/abrahambahez/scholartools/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/abrahambahez/scholartools/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/abrahambahez/scholartools/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/abrahambahez/scholartools/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/abrahambahez/scholartools/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/abrahambahez/scholartools/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/abrahambahez/scholartools/releases/tag/v0.1.0
