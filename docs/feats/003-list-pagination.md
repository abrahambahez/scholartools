# feat: list-pagination

version: 0.1
status: specced

## problem

On 2k+ record libraries, all three list endpoints dump full objects — 50+ fields per record, no pagination. Not viable for agent consumption via MCP or any token-limited context.

## decision

Uniform contract across all list operations:
- Always sorted by citekey ascending (predictable, no user-configurable sort)
- Page size fixed at 10 (not configurable for now)
- Reduced projection: only fields an agent needs to decide next action
- `total` + `page` + `pages` always present so agents know when to paginate

## shape

```
ReferenceRow: citekey, title, authors (str), year, doi, has_file, has_warnings
FileRow: citekey, path, mime_type, size_bytes
```

`authors` string: up to 5 authors as `"Family, Given; ..."`, then `"; et al."` if more.

ISBN excluded — would conflate list with search. DOI included as it's the primary dedup/fetch identifier.
`has_file` / `has_warnings` as booleans — agents only need to know presence, not the full record/list.

## blocked-by

Merge rename bug: files are archived with original filename instead of `citekey.ext`. Must be fixed before any list work — otherwise `FileRow.path` would carry wrong filenames into the library.
