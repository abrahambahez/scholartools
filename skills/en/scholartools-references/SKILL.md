---
name: scholartools-references
description: scholartools reference management — discover references from external APIs, fetch by DOI/arXiv/ISBN, extract metadata from local PDFs, stage candidates, merge into the library, and perform full CRUD on library records. Use this for any scholartools task involving finding references, adding them to the library, filtering or searching the library, updating or deleting records, or the full staging→merge workflow. If the user is doing anything research-related with scholartools that isn't purely about files or sync, use this skill.
---

## Concepts

- **Staging**: exploration scratchpad. References live here until promoted.
- **Library**: production store. Every record has a citekey assigned at merge.
- **Typical flow**: discover/fetch/extract → `stage_reference` → review → `merge`

## Discovery

```python
discover_references(query: str, sources: list[str] | None = None, limit: int = 10) -> SearchResult
# SearchResult: references: list[Reference], sources_queried: list[str], total_found: int, errors: list[str]
# sources: subset of ["crossref","semantic_scholar","arxiv","openalex","doaj","google_books"]

fetch_reference(identifier: str) -> FetchResult
# identifier: DOI, arXiv ID, or ISBN
# FetchResult: reference: Reference | None, source: str | None, error: str | None

extract_from_file(file_path: str) -> ExtractResult
# ExtractResult: reference: Reference | None, method_used: "pdfplumber"|"llm"|None, confidence: float | None, error: str | None
# Requires ANTHROPIC_API_KEY for llm fallback on scanned PDFs
```

## Staging

```python
stage_reference(ref: dict, file_path: str | None = None) -> StageResult
# StageResult: citekey: str | None, error: str | None

list_staged(page: int = 1) -> ListStagedResult
# ListStagedResult: references: list[ReferenceRow], total: int, page: int, pages: int

delete_staged(citekey: str) -> DeleteStagedResult
# DeleteStagedResult: deleted: bool, error: str | None

merge(omit: list[str] | None = None, allow_semantic: bool = False) -> MergeResult
# Promotes all staged records: validates schema, deduplicates, archives files, assigns citekeys
# omit: staged citekeys to skip this run
# allow_semantic: also promote records with uid_confidence=="semantic" (default: authoritative only)
# MergeResult: promoted: list[str], errors: dict[str, str], skipped: list[str]
```

## Library CRUD

```python
add_reference(ref: dict) -> AddResult
# AddResult: citekey: str | None, error: str | None

get_reference(citekey: str | None = None, uid: str | None = None) -> GetResult
# GetResult: reference: Reference | None, error: str | None

update_reference(citekey: str, fields: dict) -> UpdateResult
# fields: partial dict of Reference fields to overwrite
# UpdateResult: citekey: str | None, error: str | None

rename_reference(old_key: str, new_key: str) -> RenameResult
# RenameResult: old_key, new_key, error

delete_reference(citekey: str) -> DeleteResult
# DeleteResult: deleted: bool, error: str | None

list_references(page: int = 1) -> ListResult
# ListResult: references: list[ReferenceRow], total: int, page: int, pages: int

filter_references(
    query: str | None = None,    # full-text across title/abstract
    author: str | None = None,   # partial surname match
    year: int | None = None,
    ref_type: str | None = None, # CSL type: "article-journal", "book", etc.
    has_file: bool | None = None,
    staging: bool = False,       # True to filter staged records instead
    page: int = 1,
) -> ListResult
```

## Key model fields

**ReferenceRow** (list/filter results): `citekey, title, authors, year, doi, uid, has_file, has_warnings`

**Reference** (full record): `id` (=citekey), `type` (CSL), `title`, `author: [{family, given}]`,
`issued: {date-parts: [[YYYY]]}`, `DOI`, `URL`, `uid`, `uid_confidence` ("authoritative"|"semantic")
