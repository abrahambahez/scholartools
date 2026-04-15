# feat: core library — MVP

version: 0.6
status: current

## what this is

The complete MVP of scholartools. Defines the data model, port contracts, local adapter, and all public functions an agent needs to manage a reference library end-to-end: store references, search external sources, fetch full records by identifier, extract metadata from PDFs, and manage associated files.

Everything else (cloud backends, deduplication, audit, semantic search, citation graphs) depends on this being solid.

## scope

In:
- `Settings` model and `config.json` loading with local defaults
- `Reference` Pydantic model (CSL-JSON compliant)
- `FileRecord` Pydantic model (embedded in Reference)
- `StoragePort` and `FileStorePort` and `AcademicAPIPort` protocol definitions
- Local adapter: reads/writes `data/library.json`, manages `data/files/`
- CRUD service: add, get, update, delete, list references
- Citekey service: generate and assign citekeys on add
- File service: attach, detach, sync, unsync, move, list, reindex files for a reference
- Search service: keyword search across Crossref, Semantic Scholar, arXiv, OpenAlex, DOAJ, Google Books
- Fetch service: fetch full record by identifier (DOI, arXiv ID, ISSN, etc.)
- Extract service: extract metadata from a local PDF or EPUB
- All result types
- Public API wired in `__init__.py`

Out (deferred):
- Deduplication
- Audit
- Cloud adapters (S3, DynamoDB, MongoDB, GCS)
- `list_references` filtering — agents use `get_reference` or filter after listing
- Configurable page size (fixed at 10)
- Semantic search, citation graphs, social annotation

## decisions (locked)

- **Partial records on read**: `get_reference` returns a full `Reference` with `_warnings: list[str]` populated when required fields are missing. List operations surface this as `has_warnings: bool` on `ReferenceRow`. Records are never silently dropped.
- **List projection**: `list_references` and `list_files` return `ReferenceRow`/`FileRow` summaries, not full records. Use `get_reference` when the full record is needed.
- **Pagination**: all list operations return 10 records per page, sorted by citekey ascending. Page size is not configurable. Agents paginate by passing `page=N`.
- **FileRecord placement**: embedded in the `Reference` object as `_file`. Single `library.json`, no separate index.
- **Atomic writes**: write to `.library.tmp.json`, rename to `library.json`. No lock file for now — single-agent assumption.

## data model

### Reference (CSL-JSON + scholartools fields)

Pydantic models are data containers — compatible with functional style. No methods, no behavior.

```python
class Reference(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str                          # citekey — unique within the library
    type: str                        # CSL type: "article-journal", "book", etc.
    title: str | None = None
    author: list[Author] | None = None
    issued: DateField | None = None
    DOI: str | None = None
    URL: str | None = None
    added_at: datetime | None = None
    # ... all other CSL-JSON fields via extra="allow"

    # scholartools identity fields (populated at stage time via services/uid.py)
    uid: str | None = None
    uid_confidence: Literal["authoritative", "semantic"] | None = None

    # blob sync (set by sync_file; None for local-only records)
    blob_ref: str | None = None      # "sha256:{hex}" or None

    # scholartools private fields (stored with underscore aliases)
    file_record: FileRecord | None = Field(None, alias="_file")
    warnings: list[str] = Field(default_factory=list, alias="_warnings")
    field_timestamps: dict[str, str] = Field(default_factory=dict, alias="_field_timestamps")
```

Required fields for a *complete* reference: `id`, `type`, `title`, `author`, `issued`.
Missing any of these → `_warnings` populated, record still returned.

### FileRecord

```python
class FileRecord(BaseModel):
    path: str        # filename only — e.g. "graeber2017.pdf"; never an absolute path
    mime_type: str   # "application/pdf" or "application/epub+zip"
    size_bytes: int
    added_at: str    # ISO 8601
```

The library dir is always `~/.local/share/scholartools` (configurable via `local.library_dir`). Files live at `{library_dir}/files/{path}`. Storing only the filename allows the library to be relocated without invalidating records.

### ReferenceRow — list projection

Returned by `list_references` and `list_staged`. Not a full record — use `get_reference` for the complete `Reference`.

```python
class ReferenceRow(BaseModel):
    citekey: str
    title: str | None = None
    authors: str | None = None   # "Family, Given; Family, Given[; et al.]" — up to 5, then et al.
    year: int | None = None
    doi: str | None = None
    uid: str | None = None
    has_file: bool = False
    has_warnings: bool = False   # True if any required field is missing
```

### FileRow — files list projection

Returned by `list_files`. Adds `citekey` which `FileRecord` does not carry.

```python
class FileRow(BaseModel):
    citekey: str
    path: str
    mime_type: str
    size_bytes: int
```

### Library (database)

Single JSON file: array of CSL-JSON objects with `_file` and `_warnings` fields.
On first use: created automatically as `[]`. `data/files/` created automatically.

## config

Config file path: `~/.config/scholartools/config.json`. Auto-created with defaults on first run.

```json
{
  "backend": "local",
  "local": {
    "library_dir": "~/.local/share/scholartools"
  },
  "apis": {
    "email": null,
    "sources": [
      {"name": "crossref",         "enabled": true},
      {"name": "semantic_scholar", "enabled": true},
      {"name": "arxiv",            "enabled": true},
      {"name": "openalex",         "enabled": true},
      {"name": "doaj",             "enabled": true},
      {"name": "google_books",     "enabled": true}
    ]
  },
  "llm": {
    "model": "claude-sonnet-4-6"
  },
  "citekey": {
    "pattern": "{author[2]}{year}",
    "separator": "_",
    "etal": "_etal",
    "disambiguation_suffix": "letters"
  }
}
```

`apis.email` is used for Crossref polite-pool and OpenAlex; set to a real address to avoid throttling. `ANTHROPIC_API_KEY` env var enables LLM fallback in PDF extraction. `SEMANTIC_SCHOLAR_API_KEY` and `GBOOKS_API_KEY` env vars unlock higher rate limits for those sources.

Computed paths (not in config): `{library_dir}/library.json`, `{library_dir}/files/`, `{library_dir}/staging.json`, `{library_dir}/staging/`, `{library_dir}/peers/`.

## style

Functional Python throughout. Services and adapters are modules of plain functions — no classes, no `self`. Dependency injection is via `LibraryCtx`, a Pydantic model holding the active adapter functions. Services take `ctx` as a parameter; the public API wires `ctx` once at import time so agents call clean functions.

```python
# service function (async, takes ctx)
async def add_reference(ref: dict, ctx: LibraryCtx) -> AddResult: ...

# public API (sync wrapper, ctx wired lazily on first call)
def add_reference(ref: dict) -> AddResult:
    return asyncio.run(store.add_reference(ref, _get_ctx()))

# test (inject test_ctx directly, no monkeypatching)
result = await store.add_reference(ref, test_ctx)
```

## public API surface

All functions are sync. All return Result models. None raise.

### CRUD

```python
add_reference(ref: dict) -> AddResult
get_reference(citekey: str | None = None, uid: str | None = None) -> GetResult
update_reference(citekey: str, fields: dict) -> UpdateResult
rename_reference(old_key: str, new_key: str) -> RenameResult
delete_reference(citekey: str) -> DeleteResult
list_references(page: int = 1) -> ListResult   # sorted by citekey, 10/page
```

### Search and fetch

```python
discover_references(query: str, sources: list[str] | None = None, limit: int = 10) -> SearchResult
fetch_reference(identifier: str) -> FetchResult
```

`sources` defaults to all configured APIs. `identifier` is any of: DOI, arXiv ID, ISBN, ISSN — the service auto-detects type.

### File management

File operations are split into two explicit layers: local (copy/delete) and sync (S3 upload/clear):

```python
# local operations — no S3 side effects
attach_file(citekey: str, path: str) -> Result          # copy to files/, register filename
detach_file(citekey: str) -> Result                      # delete local copy, clear _file; blocked if blob_ref set
move_file(citekey: str, dest_name: str) -> MoveResult   # rename within files/
list_files(page: int = 1) -> FilesListResult             # sorted by citekey, 10/page
reindex_files() -> ReindexResult                         # repair stale absolute paths after library folder move

# sync operations — require sync block in config
sync_file(citekey: str) -> Result                        # hash → HEAD check → S3 upload → set blob_ref
unsync_file(citekey: str) -> Result                      # clear blob_ref, write unlink_file log; local file intact
get_file(citekey: str) -> Path | None                    # local path if present; S3 download if blob_ref set
prefetch_blobs(citekeys: list[str] | None = None) -> PrefetchResult   # pre-download blobs for offline use
upload_blobs() -> UploadBlobsResult                      # upload all locally-attached files that lack blob_ref
```

### PDF/EPUB extraction

```python
extract_from_file(file_path: str) -> ExtractResult
```

Does not automatically add to the library. The agent decides what to do with the result.

## citekey generation

On `add_reference`, if `id` is not provided:
- Format: `{first_author_family.lower()}{year}` → `smith2020`
- Collision: append `a`, `b`, `c` → `smith2020a`
- Missing author or year: `ref{uuid4[:6]}`

If `id` is provided, validate uniqueness — conflict returns an error in `AddResult`.

## result types

```python
class AddResult(BaseModel):
    citekey: str | None = None
    error: str | None = None

class GetResult(BaseModel):
    reference: Reference | None = None
    error: str | None = None

class ListResult(BaseModel):
    references: list[ReferenceRow]
    total: int
    page: int
    pages: int

class UpdateResult(BaseModel):
    citekey: str | None = None
    error: str | None = None

class RenameResult(BaseModel):
    old_key: str | None = None
    new_key: str | None = None
    error: str | None = None

class DeleteResult(BaseModel):
    deleted: bool
    error: str | None = None

class SearchResult(BaseModel):
    references: list[Reference]
    sources_queried: list[str]
    total_found: int
    errors: list[str]        # per-source failures, non-fatal

class FetchResult(BaseModel):
    reference: Reference | None = None
    source: str | None = None
    error: str | None = None

class ExtractResult(BaseModel):
    reference: Reference | None = None
    method_used: Literal["pdfplumber", "llm"] | None = None
    confidence: float | None = None   # 0.0–1.0
    error: str | None = None

class MoveResult(BaseModel):
    new_path: str | None = None
    error: str | None = None

class FilesListResult(BaseModel):
    files: list[FileRow]
    total: int
    page: int
    pages: int

class Result(BaseModel):
    ok: bool = True
    error: str | None = None

class ReindexResult(BaseModel):
    repaired: int
    already_ok: int
    not_found: int

class PrefetchResult(BaseModel):
    fetched: int
    already_cached: int
    errors: list[str]

class UploadBlobsResult(BaseModel):
    uploaded: int
    skipped: int
    failed: int
    errors: list[str]
```

## external API sources

Sources are declared in `config.json` as an ordered list. Order defines search priority: results from earlier sources rank higher when merging. Any source can be disabled without removing it from the config. New sources can be added by the user at any time — the library will load any source that has a registered adapter in `src/scholartools/apis/`.

Default order:

| Priority | Source           | Identifier support        | Auth required              |
|----------|------------------|---------------------------|----------------------------|
| 1        | Crossref         | DOI, keyword              | email (polite pool)        |
| 2        | Semantic Scholar | DOI, S2 ID, keyword       | API key (optional)         |
| 3        | ArXiv            | arXiv ID, keyword         | none                       |
| 4        | OpenAlex         | DOI, keyword              | email (polite pool)        |
| 5        | DOAJ             | ISSN, keyword             | none                       |
| 6        | Google Books     | ISBN                      | API key (`GBOOKS_API_KEY`) |

`discover_references` fans out across all enabled sources concurrently (httpx async). Results are normalized to `Reference`, ordered by source priority, and deduplicated by DOI before returning (DOI as dedup key only — full dedup is in feat 006).

All sources apply a retry strategy (3 attempts, 5 s delay) to handle transient API failures.

## PDF extraction pipeline

1. Run pdfplumber on the first 3 pages → extract raw text
2. Apply heuristics to identify title, authors, year, DOI, journal
3. If confidence < 0.7 or required fields missing → send PDF to Claude vision API → parse JSON response into Reference
4. Return `ExtractResult` with `method_used` and `confidence`

The agent decides whether to call `add_reference` with the result.

## local adapter behavior

- Auto-creates `{library_dir}/library.json` (`[]`) and `{library_dir}/files/` on first write if missing
- Reads: load full JSON, validate, return with warnings if fields missing
- Writes: atomic — write to `.library.tmp.json`, rename to `library.json`
- `attach_file`: copies source file into `{library_dir}/files/{citekey}.{ext}`, does not delete original; stores filename only in `FileRecord.path`
- `detach_file`: removes `_file` record, deletes file from `files/`; fails if `blob_ref` is set (call `unsync_file` first)
- `move_file`: renames within `files/` only; updates `FileRecord.path`
- `reindex_files`: repairs stale absolute paths (from pre-0.11.0 records) to filename-only format
