# spec: staging-workflow

version: 0.1
status: ready

## objective

Enable agent-human dyads to iteratively explore and curate references before committing to the production library. Agents stage references from any source, present them for human evaluation, then promote clean records via a QA gate that normalizes, deduplicates, validates, and archives.

## findings

Two stores, same `Reference` schema. Status implicit from location: `staging.json` = staged, `library.json` = production. No new fields on `Reference` except `added_at` (UTC timestamp, populated at stage time).

`merge()` is bulk by default; `omit` is the opt-out. Errors are transient — returned in `MergeResult`, never persisted. Failed records stay in staging; human must fix or delete.

Same storage adapter, different paths — no new adapter needed.

## acceptance criteria

- WHEN `stage_reference(ref, file_path=None)` is called, the system MUST assign a unique citekey, set `added_at` to current UTC, store to `staging.json`, copy file to `staging/` if provided, and return `StageResult` — never raise.

- WHEN `list_staged()` is called, the system MUST return all records in `staging.json` with `_warnings` for missing optional fields, sorted by `added_at` descending, and return `ListStagedResult` — never raise.

- WHEN `delete_staged(citekey)` is called, the system MUST remove the record from `staging.json`, delete any associated file from `staging/`, persist atomically, and return `DeleteStagedResult` — never raise.

- WHEN `merge(omit=None)` is called, the system MUST process all staged records through: normalization → duplicate detection → schema validation → file archival → promotion, returning `MergeResult` with `promoted`, `errors`, and `skipped`.

- WHEN a staged record fails any merge step, the system MUST add it to `MergeResult.errors[citekey]` with the reason, leave it in staging, and not promote it — never partially promote a record.

- WHEN `merge(omit=[citekey, ...])` is called, the system MUST skip those citekeys without processing and return them in `MergeResult.skipped`.

- WHEN duplicate detection runs, a record is a duplicate if normalized title OR ISBN-10/ISBN-13 matches an existing library record. Return the matching library citekey in the error. DOI is excluded.

- WHEN the staging store is first accessed for a write, the system MUST auto-create `staging.json` (as `[]`) and `staging/` if missing.

- WHEN merge promotes a record, the system MUST write the library atomically once after all per-record processing is complete — not incrementally.

- WHEN merge completes, the system MUST remove all promoted records from `staging.json` and delete their associated files from `staging/` — staging must contain only unpromoted records after merge.

## tasks

- [ ] task-01: extend storage adapter for staging paths
  - Add staging read/write/file ops to `adapters/local.py` (same interface, staging paths)
  - Auto-create `staging.json` and `staging/` on first write
  - Extend `LibraryCtx` or config to carry staging paths
  - tests: staging CRUD, file ops, path isolation from library

- [ ] task-02: extend models for staging result types
  - Add `added_at: datetime` to `Reference` in `models.py`
  - Add `StageResult`, `ListStagedResult`, `DeleteStagedResult`, `MergeResult` to `models.py`
  - `MergeResult`: `promoted: list[str]`, `errors: dict[str, str]`, `skipped: list[str]`
  - tests: model serialization, field validation

- [ ] task-03: staging service
  - `services/staging.py`: `stage_reference(ref, file_path, ctx)`, `list_staged(ctx)`, `delete_staged(citekey, ctx)`
  - Reuse citekey generation from core library
  - tests: CRUD, warnings, mock storage, file ops

- [ ] task-04: duplicate detection
  - `services/duplicates.py`: `normalize_title(title)`, `is_duplicate(ref, library_refs)`
  - Normalize: strip diacritics, lowercase, remove `"'?` and punctuation
  - ISBN: normalize (strip hyphens), match ISBN-10 or ISBN-13
  - tests: normalization edge cases, ISBN matching, title fixtures

- [ ] task-05: merge service
  - `services/merge.py`: `merge(omit, ctx)`
  - Per record: normalize fields → check duplicates → validate schema → archive file → collect for promotion
  - Validate schema before archiving files (prevents orphaned files on failure)
  - Write library atomically once at end
  - Remove promoted records from `staging.json` and delete their files from `staging/` after promotion
  - tests: full merge, error isolation, skip list, atomic write, file archival order, staging cleanup

- [ ] task-06: wire to public API and E2E tests
  - Add to `__init__.py`: `stage_reference`, `list_staged`, `delete_staged`, `merge`
  - Sync wrappers via `asyncio.run()`
  - E2E: `search_references` → `stage_reference` → `list_staged` → `merge` → verify library
  - tests: public API with mocked ctx, integration test with real adapters in `tmp_path`

## risks

1. **Title normalization false positives** — short or generic titles may collide. Mitigate: ISBN as secondary signal; `omit` list as manual override.
2. **File archival order** — validate schema before archiving to prevent orphaned files in `staging/` on failure.
3. **Concurrent access** — single-agent assumption inherited from core library. No locking needed now.
