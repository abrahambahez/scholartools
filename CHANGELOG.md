# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
