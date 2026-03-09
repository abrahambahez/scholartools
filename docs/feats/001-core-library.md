# feat: core library — MVP

version: 0.4
status: draft

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
- File service: link, unlink, move, list files for a reference
- Search service: keyword search across Semantic Scholar, ArXiv, Latindex, Crossref
- Fetch service: fetch full record by identifier (DOI, arXiv ID, ISSN, etc.)
- Extract service: extract metadata from a local PDF or EPUB
- All result types
- Public API wired in `__init__.py`

Out (deferred):
- Deduplication
- Audit
- Cloud adapters (S3, DynamoDB, MongoDB, GCS)
- `list_references` filtering — agents filter in Python after receiving the full list
- Semantic search, citation graphs, social annotation

## decisions (locked)

- **Partial records on read**: `get_reference` and `list_references` return records with a `warnings: list[str]` field populated when required fields are missing. Records are never silently dropped. The agent-human interface allows us to be strict about surfacing problems.
- **FileRecord placement**: embedded in the `Reference` object as `_file`. Single `library.json`, no separate index.
- **Atomic writes**: write to `.library.tmp.json`, rename to `library.json`. No lock file for now — single-agent assumption.
- **list_references filtering**: returns all records. Agents filter in Python at the consumer layer. No query language in v1.

## data model

### Reference (CSL-JSON + scholartools fields)

Pydantic models are data containers — compatible with functional style. No methods, no behavior.

```python
class Reference(BaseModel):
    model_config = ConfigDict(extra="allow")  # pass through unknown CSL-JSON fields

    id: str                          # citekey — unique within the library
    type: str                        # CSL type: "article-journal", "book", etc.
    title: str | None = None
    author: list[Author] | None = None
    issued: DateField | None = None
    DOI: str | None = None
    URL: str | None = None
    # ... all other CSL-JSON fields via extra="allow"

    _file: FileRecord | None = None  # scholartools metadata, not a CSL-JSON field
    _warnings: list[str] = []        # populated on read if required fields missing
```

Required fields for a *complete* reference: `id`, `type`, `title`, `author`, `issued`.
Missing any of these → `_warnings` populated, record still returned.

### FileRecord

```python
class FileRecord(BaseModel):
    path: str        # relative to data/files/, e.g. "smith2020.pdf"
    mime_type: str   # "application/pdf" or "application/epub+zip"
    size_bytes: int
    added_at: str    # ISO 8601
```

### Library (database)

Single JSON file: array of CSL-JSON objects with `_file` and `_warnings` fields.
On first use: created automatically as `[]`. `data/files/` created automatically.

## config

Config discovery order: `SCHOLARTOOLS_CONFIG` env var → `.scholartools/config.json` (project-local) → `~/.config/scholartools/config.json` (global). Falls back to built-in defaults if none found.

```json
{
  "backend": "local",
  "local": {
    "library_path": "data/library.json",
    "files_dir": "data/files"
  },
  "apis": {
    "sources": [
      {"name": "latindex",          "enabled": true,  "api_key": null},
      {"name": "crossref",          "enabled": true,  "api_key": null, "email": null},
      {"name": "semantic_scholar",  "enabled": true,  "api_key": null},
      {"name": "arxiv",             "enabled": true,  "api_key": null}
    ]
  },
  "llm": {
    "model": "claude-sonnet-4-6",
    "anthropic_api_key": null
  }
}
```

`anthropic_api_key` falls back to `ANTHROPIC_API_KEY` env var. `null` values mean use free/unauthenticated access where available.

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
get_reference(citekey: str) -> GetResult
update_reference(citekey: str, fields: dict) -> UpdateResult
rename_reference(old_key: str, new_key: str) -> RenameResult
delete_reference(citekey: str) -> DeleteResult
list_references() -> ListResult
```

### Search and fetch

```python
search_references(query: str, sources: list[str] | None = None, limit: int = 10) -> SearchResult
fetch_reference(identifier: str) -> FetchResult
```

`sources` defaults to all configured APIs. `identifier` is any of: DOI, arXiv ID, ISSN, PubMed ID — the service auto-detects type.

### File management

```python
link_file(citekey: str, file_path: str) -> LinkResult
unlink_file(citekey: str) -> UnlinkResult
move_file(citekey: str, dest_name: str) -> MoveResult
list_files() -> FilesListResult
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
    references: list[Reference]
    total: int

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

class LinkResult(BaseModel):
    citekey: str | None = None
    file_record: FileRecord | None = None
    error: str | None = None

class UnlinkResult(BaseModel):
    unlinked: bool
    error: str | None = None

class MoveResult(BaseModel):
    new_path: str | None = None
    error: str | None = None

class FilesListResult(BaseModel):
    files: list[FileRecord]
    total: int
```

## external API sources

Sources are declared in `config.json` as an ordered list. Order defines search priority: results from earlier sources rank higher when merging. Any source can be disabled without removing it from the config. New sources can be added by the user at any time — the library will load any source that has a registered adapter in `src/scholartools/apis/`.

Default order:

| Priority | Source           | Identifier support        | Auth required      |
|----------|------------------|---------------------------|--------------------|
| 1        | Crossref         | DOI, keyword              | email (polite)     |
| 2        | Semantic Scholar | DOI, S2 ID, keyword       | API key (optional) |
| 3        | ArXiv            | arXiv ID, keyword         | none               |
| 4        | Latindex         | ISSN, keyword             | none               |
| 5        | Google Books     | ISBN                      | API key (optional) |

`search_references` fans out across all enabled sources concurrently (httpx async). Results are normalized to `Reference`, ordered by source priority, and deduplicated by DOI before returning (DOI as dedup key only — full dedup is a separate feature).

Future sources (progressive, on demand): PubMed, CORE, BASE, DOAJ, Redalyc, SciELO.

## PDF extraction pipeline

1. Run pdfplumber on the first 3 pages → extract raw text
2. Apply heuristics to identify title, authors, year, DOI, journal
3. If confidence < 0.7 or required fields missing → send PDF to Claude vision API → parse JSON response into Reference
4. Return `ExtractResult` with `method_used` and `confidence`

The agent decides whether to call `add_reference` with the result.

## local adapter behavior

- Auto-creates `data/library.json` (`[]`) and `data/files/` on first write if missing
- Reads: load full JSON, validate, return with warnings if fields missing
- Writes: atomic — write to `data/.library.tmp.json`, rename to `data/library.json`
- `link_file`: copies source file into `data/files/{citekey}.{ext}`, does not delete original
- `move_file`: renames within `data/files/` only
- `unlink_file`: removes the `_file` record from the reference, deletes the file from `data/files/`
