# feat: core library — MVP

version: 0.13
status: current

## what this is

The complete core of scholartools. Defines the data model, port contracts, local adapter, and all public functions an agent needs to manage a reference library: store references, extract metadata from PDFs, and manage associated files.

The core package has zero network or auth dependencies. Its only runtime dependencies are `pydantic>=2.0` and `pdfplumber>=0.11`. Anything requiring httpx, anthropic, minio, or cryptography belongs in a future plugin.

## scope

In:
- `Settings` model and `config.json` loading with local defaults
- `Reference` Pydantic model (CSL-JSON compliant)
- `FileRecord` Pydantic model (embedded in Reference)
- `StoragePort` and `FileStorePort` protocol definitions
- Local adapter: reads/writes `library.json`, manages `files/`
- CRUD service: add, get, update, delete, list references
- Citekey service: generate and assign citekeys on add
- UID service: compute uid and uid_confidence on stage
- Deduplication service: uid-based duplicate detection at merge time
- File service: attach, detach, move, list, reindex, get files for a reference
- Extract service: extract metadata from a local PDF using pdfplumber; returns agent nudge when confidence is low
- Staging service: stage, list, delete staged references
- Merge service: promote staged records with dedup gate
- Filter service: local predicate search over the library
- All result types
- Public API wired in `__init__.py`

Out — proposed for future plugins:
- External API search (Crossref, Semantic Scholar, arXiv, OpenAlex, DOAJ, Google Books) → future `loretools-search` plugin
- DOI/arXiv/ISBN fetch by identifier → future `loretools-search` plugin
- LLM fallback for PDF extraction (Anthropic vision API) → future `loretools-llm` plugin
- Distributed sync (S3, change log, HLC, conflict resolution) → future `loretools-sync` plugin
- Peer management and Ed25519 signing → future `loretools-sync` plugin
- Blob content-addressed file distribution → future `loretools-sync` plugin

## decisions (locked)

- **Portability invariant**: if a module imports httpx, anthropic, minio, or cryptography, it belongs in a plugin, not core.
- **Agent nudge on extract failure**: when pdfplumber yields low confidence or no metadata, `extract_from_file` returns `ExtractResult(agent_extraction_needed=True, file_path=<path>)`. The agent passes the file to its native vision capability. Core never calls the Anthropic API.
- **Partial records on read**: `get_reference` returns a full `Reference` with `_warnings: list[str]` populated when required fields are missing. List operations surface this as `has_warnings: bool` on `ReferenceRow`. Records are never silently dropped.
- **List projection**: `list_references` and `list_files` return `ReferenceRow`/`FileRow` summaries, not full records. Use `get_reference` when the full record is needed.
- **Pagination**: all list operations return 10 records per page, sorted by citekey ascending. Page size is not configurable.
- **FileRecord placement**: embedded in the `Reference` object as `_file`. Single `library.json`, no separate index.
- **Atomic writes**: write to `.library.tmp.json`, rename to `library.json`. No lock file — single-agent assumption.
- **CWD-relative library**: config and library paths are resolved relative to the current working directory (`.scholartools/config.json`), not a fixed home-dir path. This allows per-project libraries.

## data model

### Reference (CSL-JSON + scholartools fields)

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
    uid: str | None = None
    uid_confidence: Literal["authoritative", "semantic"] | None = None

    # scholartools private fields (stored with underscore aliases)
    file_record: FileRecord | None = Field(None, alias="_file")
    warnings: list[str] = Field(default_factory=list, alias="_warnings")
```

Required fields for a *complete* reference: `id`, `type`, `title`, `author`, `issued`.
Missing any of these → `_warnings` populated, record still returned.

All other CSL-JSON fields pass through via `extra="allow"`.

### FileRecord

```python
class FileRecord(BaseModel):
    path: str        # filename only — e.g. "graeber2017.pdf"; never an absolute path
    mime_type: str
    size_bytes: int
    added_at: str    # ISO 8601
```

Files live at `{library_dir}/files/{path}`. Storing only the filename allows the library to be relocated without invalidating records.

### ReferenceRow — list projection

```python
class ReferenceRow(BaseModel):
    citekey: str
    title: str | None = None
    authors: str | None = None   # "Family, Given; Family, Given[; et al.]" — up to 5
    year: int | None = None
    doi: str | None = None
    uid: str | None = None
    has_file: bool = False
    has_warnings: bool = False
```

### FileRow — files list projection

```python
class FileRow(BaseModel):
    citekey: str
    path: str        # resolved absolute path
    mime_type: str
    size_bytes: int
```

## config

Config file path: `.scholartools/config.json` (CWD-relative). Auto-created with defaults on first run.

```json
{
  "backend": "local",
  "local": {
    "library_dir": "<cwd>"
  },
  "citekey": {
    "pattern": "{author[2]}{year}",
    "separator": "_",
    "etal": "_etal",
    "disambiguation_suffix": "letters"
  }
}
```

Only `local` and `citekey` blocks are parsed. Any extra blocks in the JSON are ignored.

## architecture

Functional Python throughout. Services and adapters are modules of plain functions — no classes, no `self`. Dependency injection is via `LibraryCtx`, a Pydantic model holding the active adapter functions.

```python
# service function (async, takes ctx)
async def add_reference(ref: dict, ctx: LibraryCtx) -> AddResult: ...

# public API (sync wrapper, ctx wired lazily on first call)
def add_reference(ref: dict) -> AddResult:
    return asyncio.run(store.add_reference(ref, _get_ctx()))
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
list_references(page: int = 1) -> ListResult
filter_references(query, author, year, ref_type, has_file, staging, page) -> ListResult
```

### Staging and merge

```python
stage_reference(ref: dict, file_path: str | None = None) -> StageResult
list_staged(page: int = 1) -> ListStagedResult
delete_staged(citekey: str) -> DeleteStagedResult
merge(omit: list[str] | None = None, allow_semantic: bool = False) -> MergeResult
```

### File management (local only)

```python
attach_file(citekey: str, path: str) -> AttachResult    # copy to files/, register filename
detach_file(citekey: str) -> DetachResult               # delete local copy, clear _file
get_file(citekey: str) -> Path | None                   # local files/ path
move_file(citekey: str, dest_name: str) -> MoveResult   # rename within files/
list_files(page: int = 1) -> FilesListResult            # sorted by citekey, 10/page
reindex_files() -> ReindexResult                        # repair stale paths after library move
```

### PDF extraction

```python
extract_from_file(file_path: str) -> ExtractResult
```

Runs pdfplumber on the first 3 pages. If confidence ≥ 0.7 and required fields are present, returns the extracted `Reference`. Otherwise returns `ExtractResult(agent_extraction_needed=True, file_path=<path>)` — the agent then uses its own vision capability to extract metadata from the file.

Does not automatically add to the library. The agent decides what to do with the result.

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

class ExtractResult(BaseModel):
    reference: Reference | None = None
    confidence: float | None = None       # 0.0–1.0; None if pdfplumber failed entirely
    error: str | None = None
    agent_extraction_needed: bool = False # True when pdfplumber cannot produce usable metadata
    file_path: str | None = None          # set when agent_extraction_needed is True

class AttachResult(BaseModel):
    citekey: str | None = None
    file_record: FileRecord | None = None
    error: str | None = None

class DetachResult(BaseModel):
    detached: bool = False
    error: str | None = None

class MoveResult(BaseModel):
    new_path: str | None = None
    error: str | None = None

class FilesListResult(BaseModel):
    files: list[FileRow]
    total: int
    page: int
    pages: int

class ReindexResult(BaseModel):
    repaired: int
    already_ok: int
    not_found: int

class StageResult(BaseModel):
    citekey: str | None = None
    error: str | None = None

class ListStagedResult(BaseModel):
    references: list[ReferenceRow]
    total: int
    page: int
    pages: int

class DeleteStagedResult(BaseModel):
    deleted: bool
    error: str | None = None

class MergeResult(BaseModel):
    promoted: list[str]
    errors: dict[str, str]
    skipped: list[str]
```

## local adapter behavior

- Auto-creates `library.json` (`[]`) and `files/` on first write if missing
- Reads: load full JSON, validate, return with warnings if fields missing
- Writes: atomic — write to `.library.tmp.json`, rename to `library.json`
- `attach_file`: copies source file into `{files_dir}/{citekey}{ext}`, stores filename only in `FileRecord.path`; does not delete original
- `detach_file`: removes `_file` record, deletes file from `files/`
- `move_file`: renames within `files/` only; updates `FileRecord.path`
- `reindex_files`: repairs stale paths (from pre-0.11.0 absolute-path records) to filename-only format
