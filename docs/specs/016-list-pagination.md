# spec: list-pagination

version: 0.1
status: ready
blocked-by: merge-rename-fix (task-01 must land first)

## objective

Replace full-record dumps in all list operations with a paginated, projected summary response. On 2k+ record libraries, dumping complete `Reference` objects is not viable for agent consumption. All three list endpoints (`list_references`, `list_staged`, `list_files`) adopt a uniform contract: total count, sorted by citekey, reduced field set, 10-record pages.

## findings

- `list_references()` and `list_staged()` return `list[Reference]` — full objects, 50+ fields per record.
- `list_staged()` sorts by `added_at` descending; this diverges from the uniform citekey sort. Will be replaced.
- `list_files()` returns `list[FileRecord]` with no citekey — useless for agent lookups.
- `merge.py:103` copies files with original filename, not `citekey.ext`. Rename logic is absent. This is a blocking bug: file records are wrong before they reach the library. Task-01 fixes it.
- External consumer `research_session.py` has three functions that iterate list results: `_list`, `_status`, `_list_staged`. They currently manually project fields from `Reference`, so the field-type change has minimal ripple — only `file_record` and `warnings` accesses need adapting via `has_file` / `has_warnings` booleans.
- Tests: ~8 assertions use `.id` on list items (rename to `.citekey`) and `f.path` on file items (preserved in `FileRow`).

## acceptance criteria

- WHEN `merge()` archives a file from staging to the library, the system MUST rename it to `{citekey}{original_extension}` in `files_dir` and update `_file.path` accordingly.

- WHEN `list_references(page)` is called, the system MUST return a `ListResult` with `items` sorted by citekey ascending, sliced to records `[(page-1)*10 : page*10]`, with `total`, `page`, and `pages` (= ceil(total/10), minimum 1).

- WHEN `list_staged(page)` is called, the system MUST return a `ListStagedResult` using the same pagination and citekey-sort contract as `list_references`.

- WHEN `list_files(page)` is called, the system MUST return a `FilesListResult` with `FileRow` items sorted by citekey ascending, paginated with the same contract.

- WHEN any list result is returned, each `ReferenceRow` MUST contain: `citekey`, `title`, `authors` (formatted string), `year` (int or null), `doi` (or null), `has_file` (bool), `has_warnings` (bool).

- WHEN formatting `authors`, the system MUST concatenate all authors as `"Family, Given"` separated by `"; "`, up to 5 authors; if more than 5, append `"; et al."` after the 5th.

- WHEN an author has only a `literal` name (no `family`/`given`), the system MUST use the `literal` value as-is in the concatenation.

- WHEN `page` is out of range (greater than `pages`), the system MUST return an empty `references`/`files` list with correct `total`, `page`, and `pages` — never raise.

- WHEN `list_files(page)` is called, each `FileRow` MUST contain: `citekey`, `path`, `mime_type`, `size_bytes`.

- WHEN any list function is called with no `page` argument, the system MUST default to page 1.

## tasks

- [ ] task-01: fix merge file rename to `citekey.ext`  *(unblocks all other tasks)*
  - `services/merge.py`: change `dest` from `Path(ctx.files_dir) / Path(file_path).name` to `Path(ctx.files_dir) / f"{citekey}{Path(file_path).suffix}"`
  - Update `_file.path` in the promoted record accordingly (already done via the `normalized["_file"]` update — just the dest path changes)
  - tests: verify promoted record's `_file.path` ends with `{citekey}.pdf` (or correct ext)

- [ ] task-02: add `ReferenceRow` and `FileRow` to `models.py`  *(blocks: task-01)*
  - `ReferenceRow`: `citekey: str`, `title: str | None`, `authors: str | None`, `year: int | None`, `doi: str | None`, `has_file: bool`, `has_warnings: bool`
  - `FileRow`: `citekey: str`, `path: str`, `mime_type: str`, `size_bytes: int`
  - Update `ListResult`: `references: list[ReferenceRow]`, add `page: int`, `pages: int`
  - Update `ListStagedResult`: same shape change
  - Update `FilesListResult`: `files: list[FileRow]`, add `page: int`, `pages: int`
  - tests: model instantiation and field presence

- [ ] task-03: pagination + projection helpers  *(blocks: task-02)*
  - Add `_format_authors(authors: list[Author] | None) -> str | None` to `services/store.py` or a shared location (pick `store.py` — it's the primary consumer)
  - Add `_paginate(items, page) -> tuple[list, int, int]` returning sliced items, page, pages
  - Add `_to_reference_row(record: dict) -> ReferenceRow`
  - tests: author formatting (0/1/5/6 authors, literal-only, mixed), pagination boundary cases (empty, page > pages, exact multiples)

- [ ] task-04: update `store.list_references`  *(blocks: task-03)*
  - Accept `page: int = 1`, sort by `id` ascending, project to `ReferenceRow`, paginate
  - tests: sort order, pagination, field projection, `has_file` / `has_warnings` values

- [ ] task-05: update `staging.list_staged`  *(blocks: task-03)*
  - Accept `page: int = 1`, replace `added_at` sort with citekey sort, project to `ReferenceRow`, paginate
  - tests: sort change, pagination, field projection

- [ ] task-06: update `files.list_files`  *(blocks: task-03)*
  - Accept `page: int = 1`, extract citekey from each record's `id`, build `FileRow`, sort by citekey, paginate
  - tests: citekey present in FileRow, sort, pagination

- [ ] task-07: update public API in `__init__.py`  *(blocks: task-04, task-05, task-06)*
  - Add `page: int = 1` to `list_references`, `list_staged`, `list_files` wrappers
  - Export `ReferenceRow`, `FileRow` from public imports

- [ ] task-08: update `research_session.py` and tests  *(blocks: task-07)*
  - `_list`: `r.id` → `r.citekey`, `r.file_record is not None` → `r.has_file`, `r.warnings or None` → `r.has_warnings or None`
  - `_status`: same field renames; `list_references()` now returns rows — counting still works
  - `_list_staged`: same field renames, drop `added_at` (not in ReferenceRow)
  - Tests: rename `r.id` → `r.citekey` (~8 assertions), verify `FileRow.path` access in `test_files.py`

## ADR required?

No — pagination is a straightforward response-shaping change with no new dependencies or architectural decisions.

## risks

- `_status` in `research_session.py` calls `list_references().references` and iterates all records to count `with_file` and `with_warnings`. After this change it only sees page 1 (10 records). **Fix**: `_status` should call a future `count` endpoint, or pass a large page to get a full count. Short-term acceptable — `_status` is informational and the `total` field is accurate. Document as a known limitation.
- `list_staged` currently sorts by `added_at` descending (newest first). Switching to citekey sort changes the agent's mental model of "what just came in". Acceptable since staging is small by design and agents can use `added_at` from `get_reference` if needed.
- `pages` minimum of 1 (even on empty stores) prevents agents from misreading 0 as an error.
