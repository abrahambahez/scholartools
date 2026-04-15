# feat 003: list pagination — paginated, projected summaries for all list endpoints

version: 0.1
status: current

## problem

`list_references()` and `list_staged()` returned full `Reference` objects — 50+ fields
each. On libraries with hundreds of records this is not viable for agent consumption.
`list_files()` returned `FileRecord` objects with no citekey, making them useless for
agent lookups.

## design

All three list endpoints return slim projected row types, sorted by citekey ascending,
10 records per page.

### `ReferenceRow` — list projection

Returned by `list_references`, `list_staged`, and `filter_references`. Not a full record
— use `get_reference(citekey)` when the complete `Reference` is needed.

```python
class ReferenceRow(BaseModel):
    citekey: str
    title: str | None = None
    authors: str | None = None   # "Family, Given; Family, Given[; et al.]" — up to 5
    year: int | None = None
    doi: str | None = None
    uid: str | None = None
    has_file: bool = False
    has_warnings: bool = False   # True if any required CSL field is missing
```

`authors` format: `"Family, Given"` joined by `"; "`. If more than 5 authors, the 6th
onwards is replaced by `"; et al."`. Authors with only a `literal` name use it as-is.

### `FileRow` — files list projection

Returned by `list_files`. Adds `citekey` which `FileRecord` does not carry.

```python
class FileRow(BaseModel):
    citekey: str
    path: str        # filename only (e.g. "graeber2017.pdf")
    mime_type: str
    size_bytes: int
```

### Paginated result types

```python
class ListResult(BaseModel):
    references: list[ReferenceRow]
    total: int
    page: int = 1
    pages: int = 1   # ceil(total/10), minimum 1

class ListStagedResult(BaseModel):
    references: list[ReferenceRow]
    total: int
    page: int = 1
    pages: int = 1

class FilesListResult(BaseModel):
    files: list[FileRow]
    total: int
    page: int = 1
    pages: int = 1
```

### Sorting

All list endpoints sort by citekey ascending. `list_staged` previously sorted by
`added_at` descending — changed to citekey for a uniform contract across all list ops.

### Page size

Fixed at 10 records per page. Not configurable. Out-of-range pages return an empty list
with correct `total`/`pages` — never raise.

### Shared helpers (`services/list_helpers.py`)

`format_authors`, `paginate`, and `to_reference_row` are extracted as a shared module
reused by `store.list_references`, `staging.list_staged`, and `files.list_files`.

## also in this change

`merge()` was fixed to rename archived files to `{citekey}{ext}` (not the original
filename from staging) when copying from `staging/` to `files/`. This was a pre-existing
bug that caused stale `_file.path` values on promoted records.
