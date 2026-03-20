---
name: scholartools-files
description: scholartools file management — link PDFs or EPUBs to library references, unlink, read file bytes, rename archived files, list all files, and prefetch blobs from S3. Use this whenever the user asks about attaching a file to a reference, accessing or downloading a PDF from the archive, auditing which references have files, renaming a stored file, or bulk-fetching blobs before processing.
---

Files are linked to **library** references (not staged ones). Each reference holds at most one file.

## Commands

```sh
scht files link <citekey> <path>
# Copies <path> into the archive and links it to the reference.

scht files unlink <citekey>
# Removes the archive copy and clears the file link.

scht files get <citekey>
# Returns file bytes (fetches from S3 if not cached locally when blob sync is active).

scht files move <citekey> <dest_name>
# Renames the archived file. dest_name is filename only, no path.

scht files list [--page N]

scht files prefetch [--citekeys key1,key2,...]
# Downloads blobs from S3 for given citekeys (all if omitted).
```

## Key model fields

**FileRow** (list results): `citekey, path, mime_type, size_bytes`

**FileRecord** (on Reference as `_file`): `path, mime_type, size_bytes, added_at`

## Notes

- To attach a file at intake time: `scht staging stage '<json>' --file <path>` — `merge` moves it to the archive.
- Run `scht files prefetch` before bulk processing to avoid repeated S3 round-trips.
