---
name: scholartools-files
description: scholartools file management — link PDFs or EPUBs to library references, unlink, read file bytes, rename archived files, list all files, and prefetch blobs from S3. Use this whenever the user asks about attaching a file to a reference, accessing or downloading a PDF from the archive, auditing which references have files, renaming a stored file, or bulk-fetching blobs before processing.
---

Files are linked to **library** references (not staged ones). Each reference holds at most one file.

## Functions

```python
link_file(citekey: str, file_path: str) -> LinkResult
# Copies file_path into the archive and links it to the reference.
# LinkResult: citekey: str | None, file_record: FileRecord | None, error: str | None

unlink_file(citekey: str) -> UnlinkResult
# Removes the archive copy and clears the file link on the reference.
# UnlinkResult: unlinked: bool, error: str | None

get_file(citekey: str) -> bytes | None
# Returns file bytes. Fetches from S3 if not cached locally (when blob sync is active).

prefetch_blobs(citekeys: list[str] | None = None) -> PrefetchResult
# Downloads blobs from S3 for the given citekeys (all if None).
# PrefetchResult: fetched: int, already_cached: int, errors: list[str]

move_file(citekey: str, dest_name: str) -> MoveResult
# Renames the archived file. dest_name is filename only, no path.
# MoveResult: new_path: str | None, error: str | None

list_files(page: int = 1) -> FilesListResult
# FilesListResult: files: list[FileRow], total: int, page: int, pages: int
```

## Key model fields

**FileRow**: `citekey, path, mime_type, size_bytes`

**FileRecord** (on Reference as `_file`): `path, mime_type, size_bytes, added_at`

## Notes

- To attach a file at intake time: `stage_reference(ref, file_path=...)` — `merge` moves it to the archive.
- Always use `get_file` to read file bytes; do not read `path` directly when blob sync is active.
- Call `prefetch_blobs` before bulk processing to avoid repeated S3 round-trips.
