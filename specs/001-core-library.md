# spec: core-library
version: 1.0
status: pending approval

## objective

Build the complete core library foundation that enables agents to reliably manage academic references end-to-end: store and retrieve references with consistent citekeys, search and fetch metadata from four external sources (Latindex, Crossref, Semantic Scholar, ArXiv), extract metadata from PDFs/EPUBs via pdfplumber with LLM fallback, and manage associated files on the local filesystem. The library is the authoritative ground truth for reference state — no silent failures, deterministic behavior, agent-optimized.

## acceptance criteria

- WHEN an agent calls `add_reference(ref)`, the system MUST assign a unique citekey if not provided (`{author_family}{year}` or `ref{uuid4[:6]}` with a/b/c collision resolution), persist atomically to `data/library.json`, and return `AddResult` with the citekey or error — never raise.
- WHEN an agent calls `get_reference(citekey)`, the system MUST return the reference with `_warnings` populated if required fields are missing, or an error if not found — never raise.
- WHEN an agent calls `list_references()`, the system MUST return all references with `_warnings` populated where applicable — never silently drop partial records.
- WHEN an agent calls `update_reference(citekey, fields)`, the system MUST merge fields, reject `id` changes that create duplicates, persist atomically, and return `UpdateResult` — never raise.
- WHEN an agent calls `delete_reference(citekey)`, the system MUST remove the reference, unlink any associated file, persist atomically, and return `DeleteResult` — never raise.
- WHEN an agent calls `search_references(query, sources, limit)`, the system MUST fan out to all enabled sources concurrently, normalize results to Reference, deduplicate by DOI, rank by source priority order from config, cap to limit, and return `SearchResult` with per-source errors as non-fatal fields — never raise.
- WHEN an agent calls `fetch_reference(identifier)`, the system MUST auto-detect identifier type (DOI, arXiv ID, ISSN, PubMed ID), fetch from the appropriate source, normalize to Reference, and return `FetchResult` — never raise.
- WHEN an agent calls `extract_from_file(file_path)`, the system MUST run pdfplumber on the first 3 pages, calculate a confidence score; if confidence < 0.7 or required fields missing, fall back to Claude vision API. Return `ExtractResult` with `method_used` and `confidence` — never raise.
- WHEN an agent calls `link_file(citekey, file_path)`, the system MUST copy the file into `data/files/{citekey}.{ext}`, create a FileRecord, embed in the Reference, persist atomically, and return `LinkResult` — never raise.
- WHEN an agent calls `unlink_file(citekey)`, the system MUST remove `_file` from the Reference, delete the file from `data/files/`, persist atomically, and return `UnlinkResult` — never raise.
- WHEN an agent calls `move_file(citekey, dest_name)`, the system MUST rename within `data/files/`, update `_file.path`, persist atomically, and return `MoveResult` — never raise.
- WHEN an agent calls `list_files()`, the system MUST return all FileRecords from all references with a total count — never raise.
- WHEN the library is first accessed for a write, the system MUST auto-create `data/library.json` (as `[]`) and `data/files/` if missing.
- WHEN a reference has missing required fields (`id`, `type`, `title`, `author`, `issued`), the system MUST populate `_warnings: list[str]` describing each missing field and return the record — never silently drop it.

## tasks

- [ ] task-01: project structure, pyproject.toml, config system
  - create `src/scholartools/` directory layout per docs/structure.md
  - define `config.json` schema, `Settings` Pydantic model, `config.py` loader with env var fallback
  - tests: loading from file, env var override, local defaults when config absent

- [ ] task-02: core Pydantic models and port Protocols (blocks: task-01)
  - `models.py`: Reference, Author, DateField, FileRecord, LibraryCtx, all Result types
  - `ports.py`: StoragePort, FileStorePort, AcademicAPIPort as `Protocol`
  - tests: Reference validation, CSL-JSON pass-through (extra="allow"), warnings population, Result model serialization

- [ ] task-03: local adapter (blocks: task-02)
  - `adapters/local.py`: `read_all`, `write_all` (atomic: write to `.tmp`, rename)
  - file ops: `copy_file`, `delete_file`, `rename_file`, `list_files`
  - auto-create `data/library.json` and `data/files/` on first write
  - tests: read/write, atomicity, file operations — all with mocked filesystem

- [ ] task-04: citekey service (blocks: task-02)
  - `services/citekeys.py`: `generate(ref)`, `resolve_collision(key, existing)` (append a/b/c)
  - fallback: `ref{uuid4[:6]}` when author or year missing
  - tests: standard generation, collision chains, missing field fallback

- [ ] task-05: CRUD service (blocks: task-03, task-04)
  - `services/store.py`: `add_reference`, `get_reference`, `update_reference`, `delete_reference`, `list_references`
  - populate `_warnings` on missing required fields; reject duplicate citekeys on add/update
  - all functions async, take `ctx: LibraryCtx`, return Result types, never raise
  - tests: full CRUD, warnings on partial records, duplicate rejection, mock storage

- [ ] task-06: file service (blocks: task-03, task-05)
  - `services/files.py`: `link_file`, `unlink_file`, `move_file`, `list_files`
  - mime_type detection (pdf → `application/pdf`, epub → `application/epub+zip`)
  - populate `FileRecord.added_at` as ISO 8601, persist Reference after modifying `_file`
  - tests: all ops, mime detection, FileRecord integrity, mock filestore

- [ ] task-07: PDF/EPUB extraction service (blocks: task-02)
  - `services/extract.py`: pdfplumber extraction (first 3 pages) → heuristic parsing (title, authors, year, DOI, journal)
  - confidence scoring; if < 0.7 or required fields missing → Claude vision API fallback
  - return `ExtractResult` with `method_used` ("pdfplumber" or "llm") and `confidence` (0.0–1.0)
  - tests: heuristics on fixture PDFs, confidence threshold logic, mocked vision API, error handling

- [ ] task-08: external API clients and search service (blocks: task-02)
  - `apis/latindex.py`, `apis/crossref.py`, `apis/semantic_scholar.py`, `apis/arxiv.py`
  - each implements `AcademicAPIPort`: `search(query, limit)` and `fetch(identifier)`
  - `services/search.py`: `search_references` fans out via `asyncio.gather`, normalizes to Reference, deduplicates by DOI, ranks by config source order, caps to limit
  - tests: each client with mocked httpx responses, fan-out logic, dedup, ranking, per-source error isolation

- [ ] task-09: fetch service (blocks: task-08)
  - `services/fetch.py`: `detect_identifier_type(identifier)` → route to correct API client
  - normalize full metadata to Reference, return `FetchResult`
  - tests: type detection for DOI/arXiv/ISSN/PubMed, routing, normalization, not-found handling

- [ ] task-10: public API wiring (blocks: task-05, task-06, task-07, task-08, task-09)
  - `__init__.py`: load config once, build `_ctx = LibraryCtx(...)` with local adapter and API clients ordered per config
  - expose sync wrappers for all 12 public functions via `asyncio.run(service_fn(args, _ctx))`
  - tests: all public functions through integration test with mock `_ctx`

- [ ] task-11: end-to-end integration tests (blocks: task-10)
  - full agent workflow: `search_references` → `fetch_reference` → `add_reference` → `extract_from_file` → `link_file` → `list_references` → `delete_reference`
  - mocked external APIs, real local adapter in `tmp_path`
  - verify citekey generation, `_warnings`, atomic writes, `FileRecord` integrity

## risks

1. **asyncio.run() + existing event loop**: callers with an active loop will get `RuntimeError`. Document the limitation; provide async service imports as escape hatch.
2. **Atomic write race**: no lock file. Single-agent assumption. Document clearly; add lock file if concurrent access becomes a requirement.
3. **PDF heuristic fragility**: PDFs are chaotic — heuristics will fail on edge cases. LLM fallback mitigates but adds cost. Test on a diverse fixture corpus and tune confidence thresholds.
4. **External API rate limits**: fan-out to 4 sources simultaneously can trigger rate limits. Collect per-source failures in `SearchResult.errors`; do not let one source failure block others.
5. **DOI-only dedup in search**: references without DOIs will not be deduplicated. Known limitation; full dedup is a separate feature.
6. **Config loaded at import time**: changing `config.json` at runtime has no effect. Document as expected behavior.
