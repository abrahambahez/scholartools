# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/abrahambahez/scholartools/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/abrahambahez/scholartools/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/abrahambahez/scholartools/releases/tag/v0.1.0
